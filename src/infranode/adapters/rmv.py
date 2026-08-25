"""RMV-HAPI-Adapter: Live-ÖPNV-Abfahrten für Frankfurt/Rhein-Main (Tier C).

Echtzeit-Abfahrtstafel je Station aus der RMV-HAPI (HAFAS-ReST-Schnittstelle,
www.rmv.de/hapi). Analog zum HVV-Geofox-Präzedenzfall ein LIVE-Request-Pfad:
minutenfrische Abfahrten inkl. Verspätung, nur für den Rhein-Main-Raum.

Auth (verifiziert 2026-07-07 gegen den Owner-accessId):
- Base ``https://www.rmv.de/hapi`` (Host hartkodiert: SSRF-Schutz).
- KEIN HMAC (anders als HVV-Geofox): der ``accessId`` ist ausschließlich ein
  Query-Parameter der Upstream-Requests. Er gelangt NIE in Cache-Key, Response
  oder Log (T-RMV-02).

Zwei Calls: ``location.name`` (Stationsname -> volle HAFAS-``id`` ``A=1@O=...@``),
dann ``departureBoard`` (Abfahrtstafel ab jetzt). Findet ``location.name`` keine
Station oder liefert ``departureBoard`` keine Abfahrten, gibt der Adapter ein
ehrliches leeres Ergebnis zurück (die Route mappt das auf ``no_data``); er wirft
NICHT für leere Resultate. HTTP-/Netzfehler werden durchgereicht (die Resilienz-
Fassade behandelt Breaker/STALE-ON-ERROR). Reine Funktion: KEIN CanonicalRecord
(das macht der Mapper), KEIN Cache/Breaker (Fassade), KEIN Archiv (Tier C,
Live-only).
"""

from __future__ import annotations

from datetime import datetime

import httpx

from infranode.adapters.hvv_geofox import _berlin_local

# Host hartkodiert (SSRF-Schutz, T-RMV-01).
_RMV_BASE = "https://www.rmv.de/hapi"


def _combine(date_str: str | None, time_str: str | None) -> datetime | None:
    """Kombiniert ``YYYY-MM-DD`` + ``HH:MM:SS`` zu einem naiven lokalen datetime.

    RMV liefert Datum und Zeit getrennt und in lokaler Wanduhrzeit (Europe/Berlin).
    Fehlt eines der beiden Felder oder ist es unparsbar, kommt None zurück (rein,
    kein Fehler). Der Tagesübergang wird über ``rtDate``/``date`` korrekt abgebildet.
    """
    if not date_str or not time_str:
        return None
    try:
        return datetime.fromisoformat(f"{date_str} {time_str}")
    except (ValueError, TypeError):
        return None


def _norm_departures(departures: list, now_local: datetime) -> list[dict]:
    """Formt die RMV-``Departure``-Liste in schlanke, stabile dicts um.

    Je Abfahrt: ``line`` (Product.line || Product.displayNumber || name),
    ``direction`` (Headsign), ``in_minutes`` (Minuten bis zur Echtzeit-Abfahrt ab
    jetzt, >=0 gekappt), ``delay_s`` (Verspätung in Sekunden, None falls kein
    ``rtTime``), ``alerts`` (leere Liste in v1; ausfallende Fahrten werden ehrlich
    vermerkt). ``now_local`` ist die naive Rhein-Main-Wanduhrzeit für die
    Countdown-Rechnung (KEINE Systemuhr im Adapter).
    """
    out: list[dict] = []
    for dep in departures or []:
        if not isinstance(dep, dict):
            continue
        product = dep.get("Product") or {}
        # HAPI liefert Product je nach Version als dict oder als Liste; defensiv
        # das erste dict nehmen.
        if isinstance(product, list):
            product = next((p for p in product if isinstance(p, dict)), {})
        line = product.get("line") or product.get("displayNumber") or dep.get("name")
        sched = _combine(dep.get("date"), dep.get("time"))
        rt = _combine(dep.get("rtDate") or dep.get("date"), dep.get("rtTime"))
        delay_s = int((rt - sched).total_seconds()) if rt and sched else None
        effective = rt or sched
        in_minutes: int | None = None
        if effective is not None:
            in_minutes = max(0, round((effective - now_local).total_seconds() / 60))
        alerts: list[str] = []
        if dep.get("cancelled"):
            alerts.append("Fahrt fällt aus")
        out.append(
            {
                "line": line,
                "direction": dep.get("direction"),
                "in_minutes": in_minutes,
                "delay_s": delay_s,
                "alerts": alerts,
            }
        )
    return out


async def fetch_rmv_departures(
    http: httpx.AsyncClient,
    *,
    slug: str,
    station: str,
    access_id: str,
    now: datetime,
) -> dict:
    """Holt Live-Abfahrten der RMV-Station ``station`` als raw-dict.

    Schritt 1 ``location.name``: löst den Stationsnamen auf die erste passende
    ``StopLocation`` auf (die volle HAFAS-``id`` ``A=1@O=...@`` wird für den
    zweiten Call gebraucht, ``extId`` ist die kurze öffentliche id). Kein Treffer
    -> ``{"slug", "stop_id": None, "stop_name": None, "departures": []}`` (kein
    Wurf, Route -> no_data). Schritt 2 ``departureBoard``: Abfahrtstafel ab jetzt.

    Rückgabe-Keys (genau das, was ``map_rmv_departures`` erwartet): ``slug``,
    ``stop_id`` (extId, Fallback volle id), ``stop_name``, ``departures`` (Liste
    schlanker dicts), ``timestamp`` (None; observed_at folgt aus der Live-Abfrage
    selbst). Der ``access_id`` steckt AUSSCHLIESSLICH in den Query-Parametern und
    taucht im Rückgabewert nicht auf (T-RMV-02).
    """
    now_local = _berlin_local(now).replace(tzinfo=None)

    resp = await http.get(
        f"{_RMV_BASE}/location.name",
        params={
            "accessId": access_id,
            "input": station,
            "format": "json",
            "maxNo": 3,
        },
    )
    resp.raise_for_status()
    body = resp.json()

    stop: dict | None = None
    for loc in body.get("stopLocationOrCoordLocation") or []:
        if isinstance(loc, dict) and isinstance(loc.get("StopLocation"), dict):
            stop = loc["StopLocation"]
            break
    if not stop or not stop.get("id"):
        return {"slug": slug, "stop_id": None, "stop_name": None, "departures": []}

    board = await http.get(
        f"{_RMV_BASE}/departureBoard",
        params={
            "accessId": access_id,
            "id": stop["id"],
            "format": "json",
            "maxJourneys": 20,
            "duration": 60,
        },
    )
    board.raise_for_status()
    board_body = board.json()

    return {
        "slug": slug,
        "stop_id": stop.get("extId") or stop.get("id"),
        "stop_name": stop.get("name"),
        "departures": _norm_departures(board_body.get("Departure"), now_local),
        "timestamp": None,
    }
