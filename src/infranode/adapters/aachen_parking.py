"""Keyloser Aachen-Parken-Adapter ``fetch_aachen_parking`` (PARK-06, Tier C).

REGRESS-KRITISCH: Aachen wird heute LIVE über ParkenDD bedient (APAG - Aachener
Parkhaus GmbH). Vor der ParkenDD-Entfernung (25-08) muss eine funktionierende
keylose Direktquelle stehen, sonst Coverage-Regress.

Direktbezug der APAG-Parkdaten über den NRW.Mobidrom-Systemadapter-Export
(mobilitaetsdaten.nrw, KEIN Mobilithek-mTLS, KEIN Key). Der Endpunkt liefert ein
JSON-Array von ``mobidp.parking.ParkingSite$Bean``-Objekten mit
``availableSpaces`` (frei), ``numberOfSpaces`` (gesamt), ``occupancyTrend``,
``isOpenNow`` sowie Koordinaten unter ``locationAndDimension.coordinatesForDisplay.
geometry.coordinates`` ([lon, lat]). Live-Realtime verifiziert 2026-07-19
(Zeitversatz-Diff: 6/20 ``availableSpaces`` in ~58 s geändert). Der Feld
``publicationTime`` ist NICHT der Live-Zeitstempel (Stammdatenstand, teils 2023) ->
``observed_at`` bleibt ehrlich ``None``.

Rückgabe ist das raw-dict, das ``map_aachen_parking`` erwartet: ``slug`` =
"aachen", ``as_of`` (None, kein verlässlicher Live-Zeitstempel) und ``facilities``
(je Einrichtung ein schlankes dict im einheitlichen Feldschema). Der Adapter baut
KEINEN ``CanonicalRecord`` und kennt KEIN Cache/Breaker (Resilienz-Fassade).
``resp.raise_for_status()`` ist Pflicht (5xx -> STALE-ON-ERROR).

LIZENZ (Owner-Entscheid 2026-07-19): Der direkte APAG-über-NRW.Mobidrom-Bezug ist
NICHT offen deklariert (CKAN ``isopen=false``, ``license_id=null``; die
Mobidrom-Nutzungsbedingungen sehen eine Registrierung vor). Daher konservativ
``LicenseId.UNKNOWN`` / ``LicenseTier.C`` (live-only, NICHT public) bis die Lizenz
bei NRW.Mobidrom/APAG schriftlich geklärt ist (voraussichtlich dl-de/by-2.0 analog
übriger Aachener Daten). Siehe ``mappers/stadt_parking.map_aachen_parking``.

Sicherheit:
- T-25-08 (SSRF): Host + Pfad in ``_BASE``/``_PATH`` hartkodiert; kein User-Input.
- T-25-09 (DoS): ``raise_for_status`` + Fassade-Timeout begrenzen den Body.
"""

from __future__ import annotations

import httpx

# Host + Systemadapter-Export-Pfad hartkodiert (SSRF-Schutz, T-25-08). Der
# gebündelte Export ``parkplaetze-apag.json`` trägt den APAG-Bezug im Pfad.
_BASE = "https://www.mobilitaetsdaten.nrw"
_PATH = "/api/systemadapter-mobilithek-exporter/parkplaetze-apag.json"


def _occupancy(free: int | None, total: int | None) -> float | None:
    """Auslastung in PROZENT (0..100) aus free/total (rein); unplausibel -> None.

    Wortgleich zu ``adapters/dortmund_parking._occupancy`` (Einheitlichkeit, eine
    Nachkommastelle).
    """
    if not isinstance(free, int) or not isinstance(total, int) or total <= 0:
        return None
    used = total - free
    if used < 0:
        return None
    return round(used / total * 100, 1)


def _coords(bean: dict) -> tuple[float | None, float | None]:
    """Liest [lon, lat] aus ``coordinatesForDisplay.geometry.coordinates`` (rein).

    GeoJSON-Reihenfolge ist [longitude, latitude]; defensiv gegen fehlende Ebenen
    -> (None, None).
    """
    geo = (
        bean.get("locationAndDimension", {})
        .get("coordinatesForDisplay", {})
        .get("geometry", {})
    )
    coords = geo.get("coordinates")
    if isinstance(coords, list) and len(coords) == 2:
        lon, lat = coords
        return (lat if isinstance(lat, (int, float)) else None), (
            lon if isinstance(lon, (int, float)) else None
        )
    return None, None


def _facility(bean: dict) -> dict:
    """Bildet ein APAG-``ParkingSite$Bean`` auf ein schlankes facility-dict ab (rein).

    Sentinel-/Plausibilitäts-Regeln wie dortmund_parking: ``free < 0`` oder
    ``free > total`` -> ``free = None`` (occupancy dann ebenfalls None). ``state``
    aus ``isOpenNow``; ``trend`` (occupancyTrend) als Zusatzfeld durchgereicht.
    """
    total = bean.get("numberOfSpaces")
    free = bean.get("availableSpaces")
    if isinstance(free, int) and (
        free < 0 or (isinstance(total, int) and free > total)
    ):
        free = None
    lat, lon = _coords(bean)
    is_open = bean.get("isOpenNow")
    return {
        "facility_id": bean.get("externalId"),
        "name": bean.get("name"),
        "lat": lat,
        "lon": lon,
        "free": free,
        "total": total,
        "occupancy": _occupancy(free, total),
        "state": ("open" if is_open else "closed") if is_open is not None else None,
        "trend": bean.get("occupancyTrend"),
        "observed_at": None,
        "url": bean.get("urlLinkAddress"),
    }


async def fetch_aachen_parking(http: httpx.AsyncClient) -> dict:
    """Holt die Live-Parkbelegung Aachen und liefert das raw-dict für den Mapper.

    Rückgabe-Keys (exakt das, was ``map_aachen_parking`` erwartet): ``slug``
    ("aachen"), ``as_of`` (None; kein verlässlicher Live-Zeitstempel im Feed) und
    ``facilities`` (Liste schlanker dicts). ``raise_for_status`` ist Pflicht
    (5xx -> Fassade STALE-ON-ERROR).
    """
    resp = await http.get(f"{_BASE}{_PATH}")
    resp.raise_for_status()
    body = resp.json()

    beans = body if isinstance(body, list) else body.get("parkingSites", []) or []
    facilities = [_facility(bean) for bean in beans]

    return {"slug": "aachen", "as_of": None, "facilities": facilities}
