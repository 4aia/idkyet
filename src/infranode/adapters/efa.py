"""Generischer keyloser Mentz-EFA-Adapter (rapidJSON) fuer Live-OePNV-Abfahrten.

EFA (Elektronische Fahrplanauskunft, Mentz GmbH) ist die verbreitete Auskunfts-
Schnittstelle vieler deutscher Verkehrsverbuende. Dieser Adapter ist bewusst
GENERISCH ueber ``base_url`` parametrisiert: die ERSTE Instanz ist der VRR
(https://efa.vrr.de/vrr, Rhein-Ruhr), der VVS Stuttgart (https://www3.vvs.de/vvs)
plugt sich spaeter mit reiner Konfiguration (anderer ``base_url`` + Slugs +
SourceId + Attribution) OHNE Adapter-Aenderung ein.

Vertrag (LIVE verifiziert 2026-07-07, keylos):
- ``base_url`` wird HINEINGEREICHT (Reuse-Ziel). Der VRR-Host wird NICHT im Adapter
  hartkodiert; der Aufrufer haelt die SSRF-Invariante (T-p9c-01), indem er eine
  Modul-Konstante uebergibt (nie User-Input).
- Schritt 1 ``XML_STOPFINDER_REQUEST`` (rapidJSON): loest den Stationsnamen auf
  eine Global-Id ``de:<AGS5>:<n>`` auf. Stadt-Scoping ueber das Praefix
  ``de:<ags5>:``; sonst erste ``type=stop``-Location; sonst leer -> no_data.
- Schritt 2 ``XML_DM_REQUEST`` (DepartureMonitor, rapidJSON): Abfahrtstafel mit
  Echtzeit. Zeiten sind ISO-8601 UTC (``...Z``) -> KEINE Zeitzonen-Mathematik
  (``datetime.fromisoformat`` parst 'Z' in Py 3.11+).

Reine Funktion: KEIN ``CanonicalRecord`` (das macht der Mapper), KEIN Cache/
Breaker (Resilienz-Fassade), KEIN Archiv (Tier C, live-only). ``raise_for_status``
ist nach jedem Call Pflicht (5xx -> STALE-ON-ERROR der Fassade). Leere/keine
Treffer -> raw mit ``departures=[]`` (KEIN Wurf, Route mappt auf no_data). ``now``
wird HINEINGEREICHT (keine Systemuhr im Adapter).
"""

from __future__ import annotations

from datetime import datetime

import httpx

# Eintraege, die mehr als diese Spanne in der Vergangenheit liegen, werden als
# klar vergangen verworfen (analog VBB-/departures-Filter). Eine kleine Toleranz
# faengt Uhr-Drift und gerade abfahrende Faelle ab.
_PAST_GRACE_SECONDS = 90


def _parse(ts: str | None) -> datetime | None:
    """ISO-8601 (inkl. 'Z') -> aware datetime, sonst None (rein, kein Fehler)."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


def _stop_event(ev: dict, now: datetime) -> tuple[datetime | None, dict]:
    """Bildet ein EFA-``stopEvent`` auf das schlanke departure-dict ab (rein).

    Rueckgabe ``(effektive_zeit, dep)``: die effektive Zeit (Echtzeit-Prognose,
    Fallback Soll) dient dem Aufrufer zum Sortieren/Filtern. ``dep`` traegt genau
    ``{line, direction, in_minutes, delay_s, alerts}`` (Kontrakt identisch
    HVV/VGN/RMV, ``TransitDeparturePayload``).
    """
    transportation = ev.get("transportation") or {}
    destination = transportation.get("destination") or {}
    planned = _parse(ev.get("departureTimePlanned"))
    estimated = _parse(ev.get("departureTimeEstimated"))
    effective = estimated or planned
    in_minutes: int | None = None
    if effective is not None:
        in_minutes = max(0, round((effective - now).total_seconds() / 60))
    delay_s: int | None = None
    if estimated is not None and planned is not None:
        delay_s = int((estimated - planned).total_seconds())
    line = transportation.get("number") or transportation.get("name")
    dep = {
        "line": line,
        "direction": destination.get("name"),
        "in_minutes": in_minutes,
        "delay_s": delay_s,
        "alerts": [],
    }
    return effective, dep


def _resolve_stop(locations: list, ags5: str) -> dict | None:
    """Waehlt die passende Location: erst Stadt-Praefix, dann erste stop-Location.

    Stadt-Scoping ueber das Global-Id-Praefix ``de:<ags5>:`` (RESEARCH-Vertrag).
    Kein Praefix-Treffer -> erste ``type=stop``-Location als Fallback. Leere/
    unpassende Antwort -> None (Route -> no_data, kein Wurf).
    """
    prefix = f"de:{ags5}:"
    fallback: dict | None = None
    for loc in locations or []:
        if not isinstance(loc, dict):
            continue
        loc_id = loc.get("id")
        if isinstance(loc_id, str) and loc_id.startswith(prefix):
            return loc
        if fallback is None and loc.get("type") == "stop":
            fallback = loc
    return fallback


def _normalize_events(events: list, now: datetime) -> list[dict]:
    """Formt ``stopEvents`` in sortierte, schlanke dicts (klar vergangene raus)."""
    items: list[tuple[datetime, dict]] = []
    for ev in events or []:
        if not isinstance(ev, dict):
            continue
        effective, dep = _stop_event(ev, now)
        # Ohne effektive Zeit oder klar in der Vergangenheit -> verwerfen.
        if effective is None:
            continue
        if (now - effective).total_seconds() > _PAST_GRACE_SECONDS:
            continue
        items.append((effective, dep))
    items.sort(key=lambda t: t[0])
    return [dep for _, dep in items]


async def fetch_efa_departures(
    http: httpx.AsyncClient,
    *,
    base_url: str,
    city_slug: str,
    ags5: str,
    station: str,
    now: datetime,
) -> dict:
    """Holt Live-Abfahrten einer EFA-Station als raw-dict (StopFinder + DM).

    ``base_url`` ist der EFA-Verbund-Endpunkt (z. B. ``https://efa.vrr.de/vrr``),
    ``ags5`` das 5-stellige AGS-Praefix der Stadt fuers Scoping, ``station`` der
    Stationsname. Rueckgabe-Keys exakt (wie ``map_efa_departures`` erwartet):
    ``slug`` (== city_slug), ``stop_id`` (Global-Id), ``stop_name``, ``departures``
    (Liste schlanker dicts), ``timestamp`` (None; observed_at folgt aus der
    Live-Abfrage). Kein Treffer / leere Antworten -> ``departures=[]`` (kein Wurf).
    """
    empty = {
        "slug": city_slug,
        "stop_id": None,
        "stop_name": None,
        "departures": [],
        "timestamp": None,
    }

    # Schritt 1: StopFinder -> Global-Id (mit Stadt-Scoping).
    sf = await http.get(
        f"{base_url}/XML_STOPFINDER_REQUEST",
        params={
            "outputFormat": "rapidJSON",
            "type_sf": "any",
            "name_sf": station,
            "coordOutputFormat": "WGS84[dd.ddddd]",
        },
    )
    sf.raise_for_status()
    stop = _resolve_stop(sf.json().get("locations") or [], ags5)
    if stop is None or not stop.get("id"):
        return empty
    global_id = stop["id"]

    # Schritt 2: DepartureMonitor -> Echtzeit-Abfahrtstafel.
    dm = await http.get(
        f"{base_url}/XML_DM_REQUEST",
        params={
            "outputFormat": "rapidJSON",
            "mode": "direct",
            "type_dm": "stop",
            "name_dm": global_id,
            "useRealtime": 1,
            "limit": 20,
        },
    )
    dm.raise_for_status()
    departures = _normalize_events(dm.json().get("stopEvents") or [], now)

    return {
        "slug": city_slug,
        "stop_id": global_id,
        "stop_name": stop.get("name"),
        "departures": departures,
        "timestamp": None,
    }
