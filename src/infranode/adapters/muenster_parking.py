"""Keyloser Münster-Parkleitsystem-Adapter ``fetch_muenster_parking`` (PARK-06, Tier A).

Direkter Zugang zur offenen Parkleitsystem-Belegung der Stadt Münster über das
Open-Data-Portal (KEIN Mobilithek-mTLS, KEIN Key). Die Quelle liefert je
Parkeinrichtung ein GeoJSON-``feature`` mit ``properties`` (id/name/adresse/lat/
lon/kapazitaet/frei/status/zeitstempel).

Rückgabe ist das raw-dict, das ``map_muenster_parking`` erwartet: ``slug`` =
"muenster", ``as_of`` (jüngster ``zeitstempel`` aller Einrichtungen) und
``facilities`` (je Einrichtung ein schlankes dict im einheitlichen Feldschema).
Der Adapter baut KEINEN ``CanonicalRecord`` und kennt KEIN Cache/Breaker (das
liefert die Resilienz-Fassade). ``resp.raise_for_status()`` ist Pflicht, damit ein
5xx als ``httpx.HTTPError`` durchschlägt und der STALE-ON-ERROR-Pfad greift.

Lizenz: Datenlizenz Deutschland Namensnennung 2.0 (DL-DE/BY 2.0), Attribution
"Stadt Münster" = Tier A. Siehe ``mappers/stadt_parking.map_muenster_parking``.

Sicherheit:
- T-25-08 (SSRF): Der Host ist in ``_BASE`` hartkodiert; es fließt kein
  User-Input in die URL (fixer Datensatz-Pfad, fixe Query).
- T-25-09 (DoS): ``raise_for_status`` + Fassade-Timeout; ``_LIMIT`` begrenzt.
"""

from __future__ import annotations

import httpx

# Host + Datensatz-Pfad hartkodiert (SSRF-Schutz, T-25-08).
_BASE = "https://opendata.stadt-muenster.de"
_DATASET = "parkleitsystem-parkhausbelegung-aktuell"
# Münster betreibt wenige Parkeinrichtungen; 100 deckt sie mit Reserve ab.
_LIMIT = 100


def _occupancy(free: int | None, capacity: int | None) -> float | None:
    """Auslastung in PROZENT (0..100) aus free/capacity (rein); unplausibel -> None.

    Wortgleich zu ``adapters/dortmund_parking._occupancy`` (Einheitlichkeit, eine
    Nachkommastelle), damit alle Parken-Quellen occupancy identisch interpretierbar
    liefern (Dortmund-Audit-Lehre 2026-06-29).
    """
    if not isinstance(free, int) or not isinstance(capacity, int) or capacity <= 0:
        return None
    used = capacity - free
    if used < 0:
        return None
    return round(used / capacity * 100, 1)


def _facility(props: dict) -> dict:
    """Bildet ein GeoJSON-``properties``-dict auf ein schlankes facility-dict ab (rein).

    Sentinel-/Plausibilitäts-Regeln wie dortmund_parking: ``free < 0`` oder
    ``free > total`` -> ``free = None`` (occupancy dann ebenfalls None).
    """
    total = props.get("kapazitaet")
    free = props.get("frei")
    if isinstance(free, int) and (
        free < 0 or (isinstance(total, int) and free > total)
    ):
        free = None
    return {
        "facility_id": props.get("id"),
        "name": props.get("name"),
        "lat": props.get("lat"),
        "lon": props.get("lon"),
        "free": free,
        "total": total,
        "occupancy": _occupancy(free, total),
        "state": props.get("status"),
        "observed_at": props.get("zeitstempel"),
        "address": props.get("adresse"),
    }


async def fetch_muenster_parking(http: httpx.AsyncClient) -> dict:
    """Holt die Live-Parkbelegung Münster und liefert das raw-dict für den Mapper.

    Rückgabe-Keys (exakt das, was ``map_muenster_parking`` erwartet): ``slug``
    ("muenster"), ``as_of`` (jüngster ``zeitstempel``, ISO-String, oder None) und
    ``facilities`` (Liste schlanker dicts). ``raise_for_status`` ist Pflicht
    (5xx -> Fassade STALE-ON-ERROR).
    """
    url = f"{_BASE}/api/records/{_DATASET}"
    resp = await http.get(url, params={"limit": _LIMIT})
    resp.raise_for_status()
    body = resp.json()

    features = body.get("features", []) or []
    facilities = [_facility(feat.get("properties", {}) or {}) for feat in features]
    timestamps = [f["observed_at"] for f in facilities if f.get("observed_at")]
    as_of = max(timestamps) if timestamps else None

    return {"slug": "muenster", "as_of": as_of, "facilities": facilities}
