"""Keyloser Hamburg-Parken-Adapter ``fetch_hamburg_parking`` (PARK-04, Tier A).

Direktbezug aus dem WFS der Hamburg Urban Platform
(``geodienste.hamburg.de/wfs_parkhaeuser``, Layer ``de.hh.up:parkhaeuser``, GML 3.2).
KEYLOS und NICHT IP-geblockt (anders als ``api.hamburg.de``, das die Box-IP sperrt) ->
umgeht den bekannten Hamburg-Block. ``srsName=EPSG:4326`` reprojiziert die UTM-
Koordinaten direkt (keine Reprojektions-Dependency).

Der Dienst deckt die gesamte HVV-Region ab (auch niedersächsische/holsteinische P+R
ohne Belegung). Für den Parken-Endpunkt sind nur die Anlagen MIT Live-Belegung
gemeint (``frei``/``gesamt``/``received`` vorhanden = das Hamburger Parkleitsystem,
~45 Häuser); rein statische Region-P+R werden verworfen (kein ``frei`` -> übersprungen).

Rückgabe ist das raw-dict, das ``map_hamburg_parking`` erwartet: ``slug`` = "hamburg",
``as_of`` (jüngster ``received``, zu ISO 8601 konvertiert) und ``facilities``. Der
Adapter baut KEINEN ``CanonicalRecord`` und kennt KEIN Cache/Breaker (Resilienz-
Fassade). ``resp.raise_for_status()`` ist Pflicht (5xx -> STALE-ON-ERROR).

Lizenz: Datenlizenz Deutschland Namensnennung 2.0 (dl-de/by-2.0) = Tier A,
Herausgeber "Freie und Hansestadt Hamburg". Siehe
``mappers/stadt_parking.map_hamburg_parking``.

Sicherheit:
- T-25-08 (SSRF): Host + WFS-Query in ``_URL`` hartkodiert; kein User-Input.
- T-25-12 (XXE/DoS): Size-Cap + Pre-Parse-Guard (DOCTYPE/ENTITY) vor dem stdlib-
  Parse; keine neue XML-Dependency (Muster ``kaiserslautern_parking``/db_timetables).
"""

from __future__ import annotations

import re
from xml.etree.ElementTree import fromstring

import httpx

# Host + WFS-2.0-GetFeature-Query hartkodiert (SSRF-Schutz, T-25-08). typeNames
# (Plural) ist WFS-2.0-Pflicht; srsName EPSG:4326 -> lon/lat statt UTM.
_URL = (
    "https://geodienste.hamburg.de/wfs_parkhaeuser"
    "?service=WFS&version=2.0.0&request=GetFeature"
    "&typeNames=parkhaeuser&srsName=EPSG:4326"
)
# Size-Cap (T-25-12): der Datensatz ist klein (~127 Anlagen); alles darüber wird nicht
# geparst (DoS-Schutz beim untrusted Live-XML).
_MAX_BYTES = 8 * 1024 * 1024
# Deutscher Zeitstempel "DD.MM.YYYY, HH:MM".
_DT_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4}),?\s*(\d{2}):(\d{2})")


def _local(tag: str) -> str:
    """Lokaler Tag-Name ohne Namespace (GML-Präfixe variieren)."""
    return tag.rsplit("}", 1)[-1]


def _guarded_parse(xml_bytes: bytes):
    """Parst GML mit Pre-Parse-Guard + Size-Cap (T-25-12); None bei Ablehnung.

    DOCTYPE/ENTITY -> Ablehnung VOR dem Parse (kein XXE/Billion-Laughs, stdlib-only);
    leerer/zu grosser Body -> None (``no_data``).
    """
    if not xml_bytes or len(xml_bytes) > _MAX_BYTES:
        return None
    if b"<!DOCTYPE" in xml_bytes or b"<!ENTITY" in xml_bytes:
        return None
    try:
        return fromstring(xml_bytes)  # noqa: S314 - Guard oben, stdlib
    except Exception:
        return None


def _to_int(value: str | None) -> int | None:
    """Parst eine Ganzzahl aus dem GML-Text (rein) oder None."""
    if value is None:
        return None
    value = value.strip()
    return int(value) if value.lstrip("-").isdigit() else None


def _iso(received: str | None) -> str | None:
    """Konvertiert den deutschen ``received``-Zeitstempel zu ISO 8601, sonst None."""
    if not received:
        return None
    m = _DT_RE.search(received)
    if not m:
        return None
    day, month, year, hour, minute = m.groups()
    return f"{year}-{month}-{day}T{hour}:{minute}:00"


def _coords(pos: str | None) -> tuple[float | None, float | None]:
    """Liest lat/lon aus ``gml:pos`` (rein); disambiguiert per Deutschland-Bereich.

    Die WFS-Achsenreihenfolge für EPSG:4326 ist mehrdeutig; die deutschen Bereiche
    (lat 47..56, lon 5..16) überlappen nicht, daher robust per Wertebereich zugeordnet.
    """
    if not pos:
        return None, None
    parts = pos.split()
    if len(parts) != 2:
        return None, None
    try:
        a, b = float(parts[0]), float(parts[1])
    except ValueError:
        return None, None
    lat = lon = None
    for val in (a, b):
        if 47.0 <= val <= 56.0:
            lat = val
        elif 5.0 <= val <= 16.0:
            lon = val
    return lat, lon


def _occupancy(free: int | None, total: int | None) -> float | None:
    """Auslastung in PROZENT (0..100) aus free/total (rein); unplausibel -> None."""
    if not isinstance(free, int) or not isinstance(total, int) or total <= 0:
        return None
    used = total - free
    if used < 0:
        return None
    return round(used / total * 100, 1)


def _facility(props: dict, pos: str | None) -> dict | None:
    """Bildet ein Parkhaus-Member auf ein facility-dict ab (rein); None wenn kein Live.

    Nur Anlagen MIT Live-Belegung (``frei`` vorhanden) sind gemeint; sonst None (die
    statischen Region-P+R werden verworfen). Sentinel wie dortmund_parking.
    """
    if "frei" not in props:
        return None
    free = _to_int(props.get("frei"))
    total = _to_int(props.get("gesamt")) or _to_int(props.get("stellplaetze_gesamt"))
    if isinstance(free, int) and (
        free < 0 or (isinstance(total, int) and free > total)
    ):
        free = None
    lat, lon = _coords(pos)
    return {
        "facility_id": props.get("_gml_id"),
        "name": props.get("name"),
        "lat": lat,
        "lon": lon,
        "free": free,
        "total": total,
        "occupancy": _occupancy(free, total),
        "state": props.get("status") or props.get("situation"),
        "observed_at": _iso(props.get("received")),
    }


def parse_hamburg_parking(xml_bytes: bytes) -> list[dict]:
    """Parst die GML-FeatureCollection zu facility-dicts (rein, gehärtet).

    Namespace-agnostisch über lokale Tag-Namen (GML-Präfixe variieren je Publisher).
    Nur Anlagen mit Live-Belegung werden aufgenommen.
    """
    root = _guarded_parse(xml_bytes)
    if root is None:
        return []
    facilities: list[dict] = []
    for feat in root.iter():
        if _local(feat.tag) != "parkhaeuser":
            continue
        props: dict = {}
        gml_id = feat.get("{http://www.opengis.net/gml/3.2}id") or feat.get("id")
        if gml_id:
            props["_gml_id"] = gml_id
        pos: str | None = None
        for child in feat.iter():
            ln = _local(child.tag)
            if ln == "pos":
                pos = (child.text or "").strip() or None
            elif ln != "parkhaeuser" and child.text is not None:
                props.setdefault(ln, child.text.strip())
        fac = _facility(props, pos)
        if fac is not None:
            facilities.append(fac)
    return facilities


async def fetch_hamburg_parking(http: httpx.AsyncClient) -> dict:
    """Holt die Live-Parkbelegung Hamburg (dl-de/by-WFS) und liefert das raw-dict.

    Rückgabe-Keys (exakt was ``map_hamburg_parking`` erwartet): ``slug`` ("hamburg"),
    ``as_of`` (jüngster ``received`` als ISO-String oder None) und ``facilities``.
    ``raise_for_status`` ist Pflicht (5xx -> Fassade STALE-ON-ERROR).
    """
    resp = await http.get(_URL)
    resp.raise_for_status()
    facilities = parse_hamburg_parking(resp.content)

    timestamps = [f["observed_at"] for f in facilities if f["observed_at"]]
    as_of = max(timestamps) if timestamps else None
    return {"slug": "hamburg", "as_of": as_of, "facilities": facilities}
