"""Keyloser Karlsruhe-Parken-Adapter ``fetch_karlsruhe_parking`` (PARK-06, Tier A).

REGRESS-KRITISCH: Karlsruhe wird heute LIVE über ParkenDD bedient. Der Direktbezug
löst den ParkenDD-Karlsruhe-Pfad ab.

Direktbezug aus dem offiziellen, CC-BY-4.0-lizenzierten Parkhaus-Datensatz der Stadt
Karlsruhe (Transparenzportal ``transparenz.karlsruhe.de/dataset/parkhaeuser``), der
als keyloser WFS 2.0 GeoServer-Dienst ausgeliefert wird
(``mobil.trk.de/geoserver/TBA/ows``, Layer ``TBA:parkhaeuser``). Der Dienst deckt die
gesamte TechnologieRegion Karlsruhe ab (mehrere Gemeinden), daher wird auf
``gemeinde == "Karlsruhe"`` gefiltert (sonst Fremdstädte wie Baden-Baden/Rastatt).
20 Karlsruher Parkhäuser tragen Echtzeit-Belegung (``echtzeit_belegung="T"``:
``freie_parkplaetze`` + ``gesamte_parkplaetze`` + Live-Zeitstempel
``stand_freieparkplaetze``); die IDs sind deckungsgleich mit dem alten
web1.karlsruhe.de-Parkleitsystem (dieselbe Datenbasis, aber offiziell lizenziert und
maschinenlesbar als JSON statt HTML).

Rückgabe ist das raw-dict, das ``map_karlsruhe_parking`` erwartet: ``slug`` =
"karlsruhe", ``as_of`` (jüngster ``stand_freieparkplaetze``) und ``facilities``. Der
Adapter baut KEINEN ``CanonicalRecord`` und kennt KEIN Cache/Breaker (Resilienz-
Fassade). ``resp.raise_for_status()`` ist Pflicht (5xx -> STALE-ON-ERROR).

Lizenz: Creative Commons Namensnennung 4.0 International (CC-BY 4.0), Herausgeber
"Stadt Karlsruhe" = Tier A (Transparenzportal-Datensatz ``parkhaeuser`` verifiziert
2026-07-19: ``license_id = cc-by/4.0``). Siehe
``mappers/stadt_parking_b.map_karlsruhe_parking``.

Sicherheit:
- T-25-08 (SSRF): Host + WFS-Query in ``_URL`` hartkodiert; kein User-Input.
- T-25-09 (DoS): ``raise_for_status`` + Fassade-Timeout begrenzen den Body.
"""

from __future__ import annotations

import httpx

# Host + WFS-2.0-GetFeature-Query hartkodiert (SSRF-Schutz, T-25-08). srsName
# EPSG:4326 -> der GeoServer reprojiziert die UTM-Koordinaten direkt nach lon/lat
# (kein Reprojektions-Dependency nötig). typeNames (Plural) ist WFS-2.0-Pflicht.
_URL = (
    "https://mobil.trk.de/geoserver/TBA/ows"
    "?service=WFS&version=2.0.0&request=GetFeature"
    "&typeNames=TBA:parkhaeuser&outputFormat=application/json&srsName=EPSG:4326"
)
# Der WFS deckt die ganze Region ab; nur die Karlsruher Anlagen sind gemeint.
_GEMEINDE = "Karlsruhe"


def _occupancy(free: int | None, total: int | None) -> float | None:
    """Auslastung in PROZENT (0..100) aus free/total (rein); unplausibel -> None."""
    if not isinstance(free, int) or not isinstance(total, int) or total <= 0:
        return None
    used = total - free
    if used < 0:
        return None
    return round(used / total * 100, 1)


def _facility(feat: dict) -> dict | None:
    """Bildet ein WFS-Feature auf ein schlankes facility-dict ab (rein); None -> skip.

    Einträge ohne Kapazität UND ohne freie Plätze (keine verwertbaren Daten) ->
    None. Ohne Echtzeit-Belegung (``echtzeit_belegung != "T"``) bleibt ``free``
    ehrlich None (bekanntes Parkhaus ohne Live-Wert). Sentinel wie dortmund_parking:
    ``free < 0``/``free > total`` -> ``free = None``.
    """
    props = feat.get("properties", {}) or {}
    total = props.get("gesamte_parkplaetze")
    free = (
        props.get("freie_parkplaetze")
        if props.get("echtzeit_belegung") == "T"
        else None
    )
    if total is None and free is None:
        return None
    if isinstance(free, int) and (
        free < 0 or (isinstance(total, int) and free > total)
    ):
        free = None

    lat = lon = None
    coords = (feat.get("geometry") or {}).get("coordinates")
    if isinstance(coords, list) and len(coords) == 2:
        lon, lat = coords  # GeoJSON-Reihenfolge [lon, lat]

    geschlossen = props.get("geschlossen")
    state = (
        {"T": "closed", "F": "open"}.get(geschlossen)
        if isinstance(geschlossen, str)
        else None
    )
    return {
        "facility_id": props.get("id"),
        "name": props.get("parkhaus_name"),
        "lat": lat,
        "lon": lon,
        "free": free,
        "total": total,
        "occupancy": _occupancy(free, total),
        "state": state,
        "observed_at": props.get("stand_freieparkplaetze"),
    }


async def fetch_karlsruhe_parking(http: httpx.AsyncClient) -> dict:
    """Holt die Live-Parkbelegung Karlsruhe (CC-BY-4.0-WFS) und liefert das raw-dict.

    Filtert auf ``gemeinde == "Karlsruhe"`` (der WFS deckt die ganze Region ab).
    Rückgabe-Keys (exakt was ``map_karlsruhe_parking`` erwartet): ``slug``
    ("karlsruhe"), ``as_of`` (jüngster ``stand_freieparkplaetze``, ISO-String oder
    None) und ``facilities``. ``raise_for_status`` ist Pflicht (5xx -> Fassade
    STALE-ON-ERROR).
    """
    resp = await http.get(_URL)
    resp.raise_for_status()
    body = resp.json()

    facilities: list[dict] = []
    for feat in body.get("features", []) or []:
        if (feat.get("properties") or {}).get("gemeinde") != _GEMEINDE:
            continue
        fac = _facility(feat)
        if fac is not None:
            facilities.append(fac)

    timestamps = [f["observed_at"] for f in facilities if f["observed_at"]]
    as_of = max(timestamps) if timestamps else None

    return {"slug": "karlsruhe", "as_of": as_of, "facilities": facilities}
