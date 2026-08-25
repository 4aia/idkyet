"""DWD-Wetterwarnungen-Adapter über Brightsky-Alerts (GeoNutzV, Tier A).

Der DWD hat seine alte bundesweite Warn-JSON-Schnittstelle (JSONP, ein File
für alle Warncells) am 2026-07-16 global abgeschaltet (404, verifiziert von
zwei Netzen aus). Die
Warnungen kommen seitdem über die keylose Brightsky-Alerts-API
(``https://api.brightsky.dev/alerts``), die dieselben amtlichen DWD-CAP-
Meldungen ausliefert; Brightsky ist bereits der Bezugsweg der weather-Quelle
(``adapters/dwd.py``). Abruf je Stadt per lat/lon aus dem Städte-Register
(die frühere "1"+AGS-Warncell-Ableitung passt für Brightsky nicht, mindestens
nicht für Stadtstaaten); die zuständige Warncell liefert Brightsky in
``location.warn_cell_id`` gleich mit.

Mapping je Alert (nur ``status == "actual"``, Test-Meldungen werden verworfen):
``level`` entsteht aus der CAP-severity (minor=1, moderate=2, severe=3,
extreme=4; unbekannt/fehlend -> None), ``start``/``end`` sind die amtlichen
CAP-Zeiten ``onset``/``expires`` und werden als ISO-8601-Strings unverändert
durchgereicht (früher Epoch-Millisekunden, keine Rückkonvertierung).

KRITISCH (Audit K5): Hitze-/UV-Gesundheitswarnungen dürfen ``max_level`` nicht
überstrahlen. Die Erkennung läuft jetzt über das geschlossene Brightsky-Enum
``category`` (``met`` | ``health``) statt über die frühere Sondercode-Skala
(Code >= 50): ``max_level`` wird AUSSCHLIESSLICH über ``met``-Warnungen mit
bekannter Stufe gebildet; ``health``-Warnungen werden NICHT verworfen, sondern
separat in ``special_warnings`` geführt (Teilmenge von ``warnings``).

Sicherheit (T-05-03 SSRF): Host in ``_URL`` hartkodiert; lat/lon stammen aus
dem validierten Städte-Register (``entry.geo``) und fließen nur als
Query-Parameter ein. ``raise_for_status`` ist Pflicht (5xx -> Resilienz-
Fassade, stale-on-error).
"""

from __future__ import annotations

import httpx

# Host hartkodiert (SSRF-Schutz, T-05-03).
_URL = "https://api.brightsky.dev/alerts"

# CAP-severity -> Warnstufe 1-4. Unbekannte/fehlende severity -> None (zählt
# nicht in max_level, kein Raten; defensive Behandlung).
_SEVERITY_LEVEL = {"minor": 1, "moderate": 2, "severe": 3, "extreme": 4}


async def fetch_dwd_warnings(
    http: httpx.AsyncClient, *, slug: str, lat: float, lon: float
) -> dict:
    """Holt aktive amtliche DWD-Warnungen einer Stadt via Brightsky-Alerts.

    Rückgabe ``{warncell_id, count, max_level, warnings, special_warnings}``
    (unverändertes raw-Format für ``map_dwd_warnings``): ``warnings`` enthält
    ALLE ausgelieferten Warnungen (regulär + health) als dicts mit
    ``event``/``level``/``headline``/``start``/``end`` (start/end = ISO-8601
    aus onset/expires); ``special_warnings`` ist die Teilmenge mit
    ``category == "health"`` (Hitze/UV, Audit K5); ``max_level`` die höchste
    Stufe der regulären (``met``-)Warnungen, 0 wenn keine (ehrliche
    Ruhe-Basislinie, nie None). ``warncell_id`` kommt aus
    ``location.warn_cell_id`` der Antwort (fehlt location -> None) und bleibt
    NUR im raw-dict (kein Payload-Feld). ``slug`` dient der Symmetrie zum
    Wetter-Adapter (Cache-Key/Debugging in der Route).
    """
    resp = await http.get(_URL, params={"lat": lat, "lon": lon})
    resp.raise_for_status()
    body = resp.json()

    warnings: list[dict] = []
    special_warnings: list[dict] = []
    regular_levels: list[int] = []
    for alert in body.get("alerts") or []:
        # Nur amtliche Meldungen ausliefern; status "test" wird verworfen.
        if alert.get("status") != "actual":
            continue
        level = _SEVERITY_LEVEL.get(alert.get("severity"))
        warning = {
            "event": alert.get("event_de"),
            "level": level,
            "headline": alert.get("headline_de"),
            "start": alert.get("onset"),
            "end": alert.get("expires"),
        }
        warnings.append(warning)
        if alert.get("category") == "health":
            # Audit K5: Gesundheitswarnungen separat, NICHT in max_level.
            special_warnings.append(warning)
        elif level is not None:
            regular_levels.append(level)

    location = body.get("location") or {}
    warn_cell = location.get("warn_cell_id")
    return {
        "warncell_id": str(warn_cell) if warn_cell is not None else None,
        "count": len(warnings),
        "max_level": max(regular_levels) if regular_levels else 0,
        "warnings": warnings,
        "special_warnings": special_warnings,
    }
