"""Keyloser Oldenburg-Parken-Adapter ``fetch_oldenburg_parking`` (PARK-06, Tier A).

Direkter Zugang zum offenen Parkleitsystem der Stadt Oldenburg über das
Open-Data-Portal (KEIN Mobilithek-mTLS, KEIN Key, 5-Minuten-Aktualisierung). Die
Quelle liefert je Parkeinrichtung ein flaches Record (id/name/strasse/lat/lon/
gesamt/frei/geschlossen/stand).

Rückgabe ist das raw-dict, das ``map_oldenburg_parking`` erwartet: ``slug`` =
"oldenburg", ``as_of`` (jüngster ``stand`` aller Einrichtungen) und ``facilities``
(je Einrichtung ein schlankes dict im einheitlichen Feldschema). Der Adapter baut
KEINEN ``CanonicalRecord`` und kennt KEIN Cache/Breaker (das liefert die
Resilienz-Fassade). ``resp.raise_for_status()`` ist Pflicht, damit ein 5xx als
``httpx.HTTPError`` durchschlägt und der STALE-ON-ERROR-Pfad greift.

Lizenz: Datenlizenz Deutschland Namensnennung 2.0 (DL-DE/BY 2.0), Attribution
"Stadt Oldenburg (Oldb)" = Tier A. Siehe
``mappers/stadt_parking.map_oldenburg_parking``.

Sicherheit:
- T-25-08 (SSRF): Der Host ist in ``_BASE`` hartkodiert; es fließt kein
  User-Input in die URL (fixer Datensatz-Pfad, fixe Query).
- T-25-09 (DoS): ``raise_for_status`` + Fassade-Timeout; ``_LIMIT`` begrenzt.
"""

from __future__ import annotations

import httpx

# Host + Datensatz-Pfad hartkodiert (SSRF-Schutz, T-25-08).
_BASE = "https://opendata.oldenburg.de"
_DATASET = "parkleitsystem-belegung"
# Oldenburg betreibt wenige Parkeinrichtungen; 100 deckt sie mit Reserve ab.
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


def _facility(rec: dict) -> dict:
    """Bildet ein Oldenburg-Record auf ein schlankes facility-dict ab (rein).

    Sentinel-/Plausibilitäts-Regeln wie dortmund_parking: ``free < 0`` oder
    ``free > total`` -> ``free = None`` (occupancy dann ebenfalls None). Der
    boolesche ``geschlossen``-Zustand wird auf ``state`` ("geschlossen"/"offen")
    abgebildet.
    """
    total = rec.get("gesamt")
    free = rec.get("frei")
    if isinstance(free, int) and (
        free < 0 or (isinstance(total, int) and free > total)
    ):
        free = None
    geschlossen = rec.get("geschlossen")
    state = None if geschlossen is None else "geschlossen" if geschlossen else "offen"
    return {
        "facility_id": rec.get("id"),
        "name": rec.get("name"),
        "lat": rec.get("lat"),
        "lon": rec.get("lon"),
        "free": free,
        "total": total,
        "occupancy": _occupancy(free, total),
        "state": state,
        "observed_at": rec.get("stand"),
        "address": rec.get("strasse"),
    }


async def fetch_oldenburg_parking(http: httpx.AsyncClient) -> dict:
    """Holt die Live-Parkbelegung Oldenburg und liefert das raw-dict für den Mapper.

    Rückgabe-Keys (exakt das, was ``map_oldenburg_parking`` erwartet): ``slug``
    ("oldenburg"), ``as_of`` (jüngster ``stand``, ISO-String, oder None) und
    ``facilities`` (Liste schlanker dicts). ``raise_for_status`` ist Pflicht
    (5xx -> Fassade STALE-ON-ERROR).
    """
    url = f"{_BASE}/api/records/{_DATASET}"
    resp = await http.get(url, params={"limit": _LIMIT})
    resp.raise_for_status()
    body = resp.json()

    records = body.get("parkhaeuser", []) or []
    facilities = [_facility(rec) for rec in records]
    timestamps = [f["observed_at"] for f in facilities if f.get("observed_at")]
    as_of = max(timestamps) if timestamps else None

    return {"slug": "oldenburg", "as_of": as_of, "facilities": facilities}
