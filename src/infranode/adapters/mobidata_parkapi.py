"""Keyloser MobiData-BW-ParkAPI-v3-Adapter ``fetch_mobidata_parking`` (PARK-01/02).

Direkter Bezug der Live-Parkbelegung Baden-Württembergs über die keylose ParkAPI v3
von MobiData BW (live verifiziert 2026-07-19). Anders als beim DATEX-Frankfurt-Muster
ist KEIN Zwei-Feed-Join nötig: ein einziger GET je ``source_uid`` liefert Stammdaten
UND Realtime-Belegung inline:

- GET ``{_BASE}/park-api/api/public/v3/parking-sites?source_uid=<uid>`` liefert je Site
  ein flaches Objekt mit ``name``/``address``/``lat``/``lon``/``capacity``/``type``/
  ``purpose`` und bei ``has_realtime_data == true`` zusätzlich
  ``realtime_free_capacity``/``realtime_capacity``/``realtime_opening_status``/
  ``realtime_data_updated_at``.

Mehrere ``source_uids`` je Stadt (z.B. P+R-Teilbestände) werden zu EINER
facilities-Liste zusammengeführt. Rückgabe ist das raw-dict, das
``map_mobidata_parking`` erwartet: ``slug``, ``facilities`` (je Site ein schlankes
dict mit dem quellenübergreifenden Zielfeldschema) und ``as_of`` (jüngster
``realtime_data_updated_at`` aller Sites, sonst None).

Der Adapter baut KEINEN ``CanonicalRecord`` und kennt KEIN Cache/Breaker (das liefert
die Resilienz-Fassade); die Lizenz je Stadt liegt im Mapper. ``resp.raise_for_status()``
ist Pflicht, damit ein 5xx als ``httpx.HTTPError`` durchschlägt und der
STALE-ON-ERROR-Pfad greift.

Sicherheit:
- T-25-04 (SSRF): Der Host ist in ``_BASE`` hartkodiert; die ``source_uids`` stammen
  ausschließlich aus der kuratierten Connector-Registry (25-07), NIE aus rohem
  User-Input. Es fließt kein Nutzer-Wert in den Host der URL.
- T-25-05 (DoS): ``resp.raise_for_status`` + die Fassade-Timeouts begrenzen den
  Bezug; es wird kein unbeschränkter Body gestreamt.

Lizenz je Stadt: siehe ``mappers/mobidata_parkapi.map_mobidata_parking``.
"""

from __future__ import annotations

import httpx

# Host hartkodiert (SSRF-Schutz, T-25-04); source_uid kommt aus der kuratierten Map.
_BASE = "https://api.mobidata-bw.de"


def _occupancy(free: object, capacity: object) -> float | None:
    """Auslastung in PROZENT (0..100) aus free/capacity (rein); unplausibel -> None.

    Audit-Rerun (2026-06-29): vorher 0..1 (Anteil) zurückgegeben, während alle
    anderen Parken-Quellen (Wuppertal/Magdeburg/Frankfurt via Mobilithek, DATEX-3)
    UND die MCP-Doku "occupancy %" Prozent liefern. Dortmund war der einzige
    Ausreißer -> Konsumenten konnten occupancy nicht einheitlich interpretieren.
    Jetzt einheitlich Prozent, eine Nachkommastelle (wie Magdeburg/Wuppertal).
    """
    if not isinstance(free, int) or not isinstance(capacity, int) or capacity <= 0:
        return None
    used = capacity - free
    if used < 0:
        return None
    return round(used / capacity * 100, 1)


def _facility(it: dict) -> dict:
    """Bildet ein ParkAPI-v3-parking-site auf das Zielfeldschema ab (rein).

    Realtime-Felder inline (kein Zwei-Feed-Join): ``free`` = ``realtime_free_capacity``,
    ``total`` = ``realtime_capacity`` oder ersatzweise ``capacity``. Sentinel-Regeln
    (H8, analog ``adapters/parkendd``): ``free < 0`` -> None; unplausibel
    ``free > total`` (bei ``total > 0``) -> None. Ohne Realtime bleibt ``free`` None
    (Stammdaten ehrlich mitgegeben).
    """
    total = it.get("realtime_capacity") or it.get("capacity")
    free = it.get("realtime_free_capacity")
    if isinstance(free, (int, float)) and free < 0:  # Sentinel -> None (H8)
        free = None
    if (
        isinstance(free, (int, float))
        and isinstance(total, (int, float))
        and total > 0
        and free > total
    ):  # unplausibel: mehr frei als vorhanden
        free = None
    return {
        "name": it.get("name"),
        "address": it.get("address"),
        "lat": it.get("lat"),
        "lon": it.get("lon"),
        "free": free,
        "total": total,
        "occupancy": _occupancy(free, total),
        "state": it.get("realtime_opening_status"),
        "lot_type": it.get("purpose") or it.get("type"),
        "observed_at": it.get("realtime_data_updated_at"),
    }


async def fetch_mobidata_parking(
    http: httpx.AsyncClient,
    *,
    slug: str,
    source_uids: list[str],
    lat: float | None = None,
    lon: float | None = None,
) -> dict:
    """Holt die Live-Parkbelegung je ``source_uid`` und führt sie je Stadt zusammen.

    Schleife über die kuratierten ``source_uids`` (SSRF: nur aus der Registry, nie
    roher User-Input): je uid EIN GET auf ``parking-sites?source_uid=<uid>``,
    ``resp.raise_for_status()`` (5xx -> Fassade STALE-ON-ERROR), Items -> ``_facility``,
    alle facilities zusammengeführt. Rückgabe-Keys exakt wie vom Mapper erwartet:
    ``slug``, ``facilities`` (kann leer sein -> no_data-Pfad in der Route) und ``as_of``
    (jüngster ``realtime_data_updated_at`` aller Sites, sonst None).

    ``lat``/``lon`` sind Teil der einheitlichen Connector-Signatur; ParkAPI benötigt sie
    nicht (die Auswahl erfolgt über die source_uid), sie bleiben daher ungenutzt.
    """
    url = f"{_BASE}/park-api/api/public/v3/parking-sites"
    facilities: list[dict] = []
    timestamps: list[str] = []
    for uid in source_uids:
        resp = await http.get(url, params={"source_uid": uid})
        resp.raise_for_status()
        for it in resp.json().get("items", []) or []:
            facilities.append(_facility(it))
            stamp = it.get("realtime_data_updated_at")
            if stamp:
                timestamps.append(stamp)
    return {
        "slug": slug,
        "facilities": facilities,
        "as_of": max(timestamps) if timestamps else None,
    }
