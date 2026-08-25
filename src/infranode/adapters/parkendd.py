"""ParkenDD-Adapter fetch_parkendd (DATA-40, Live-Parkhaus-Belegung, Tier C).

ParkenDD (https://api.parkendd.de, https://github.com/ParkenDD) ist ein offener
Aggregator, der die Parkhaus-Belegung vieler deutscher Städte aus deren
amtlichen Parkleitsystemen bündelt und keylos als JSON bereitstellt. Ein einziger
Adapter erschließt damit viele InfraNode-Städte gleichzeitig (Dedup-Prinzip:
EIN Parking-Endpunkt mit ParkenDD als bevorzugter Live-Quelle, statt je Stadt ein
eigener Connector).

LIZENZ (B-1, GOV-01): ParkenDD aggregiert heterogen lizenzierte Stadt-Quellen und
deklariert KEINE einheitliche Lizenz. Die Lizenz wird daher PRO STADT am echten
Ursprung verifiziert (``mappers/parkendd._PARKENDD_LICENSE``). Nur Städte mit
offener Standardlizenz werden überhaupt ausgeliefert (Owner-Entscheidung
2026-06-23: keine Tier-B/C-/NC-Auslieferung), die übrigen sind aus
``PARKENDD_CITIES`` entfernt und damit not_covered. Reine Live-Daten -> KEIN Archiv.

Sicherheit (T-9-02 SSRF): Host hartkodiert in ``_BASE``. Die Stadt-ID stammt aus
der hartkodierten ``PARKENDD_CITIES``-Map (kein roher Nutzer-Input in der URL).

DoS-/Datenfehler-Schutz: ``resp.raise_for_status()`` (5xx -> HTTPError -> STALE-
ON-ERROR der Fassade); jeder Feldzugriff defensiv per ``.get()`` mit None-Fallback.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import structlog

log = structlog.get_logger()

_BASE = "https://api.parkendd.de"

# Staleness-Guard (Owner-Entscheidung (b), 2026-07-07): 8 der 13 ParkenDD-Städte
# sind beim Upstream EINGEFROREN (last_updated koeln 2021-09, heilbronn 2022-09,
# dortmund/ulm 2023-12, oldenburg 2024-02, heidelberg 2024-08, muenster 2024-11,
# hamburg 2025-03; nur aachen/dresden/freiburg/kaiserslautern/karlsruhe live).
# Eine Live-Belegung, deren Datenstand aelter als dieses Fenster ist, ist keine
# Belegungsauskunft mehr -> der Fetch leert ``facilities`` und der bestehende
# ehrliche no_data-Pfad der Route greift. Selbstheilend: liefert der Ursprung
# wieder, faellt die Stadt automatisch auf ok zurueck. 48 h statt Stunden, damit
# kurze Upstream-Wartungen nicht flappen; die eingefrorenen Staedte liegen um
# GROESSENORDNUNGEN darueber. Live-Zellen je Stadt siehe expected_matrix-Pflege.
_MAX_AS_OF_AGE = timedelta(hours=48)


def _is_frozen(as_of: object, *, now: datetime | None = None) -> bool:
    """True, wenn der ParkenDD-Datenstand aelter als ``_MAX_AS_OF_AGE`` ist.

    Defensiv: fehlender oder unparsbarer ``last_updated``-String gilt NICHT als
    eingefroren (kein falsches no_data aus einem Formatwechsel; die Frische ist
    dann schlicht unbekannt). ParkenDD liefert naive Zeitstempel; sie werden als
    UTC interpretiert (moegliche Lokalzeit-Abweichung von 1-2 h ist gegen das
    48-h-Fenster irrelevant).
    """
    if not isinstance(as_of, str) or not as_of:
        return False
    try:
        parsed = datetime.fromisoformat(as_of)
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return (now or datetime.now(UTC)) - parsed > _MAX_AS_OF_AGE


# ParkenDD antwortet seit ~2026-07 traege (gemessen 2026-07-07 von der Box:
# 1,6-4,2s TTFB, Spitzen darueber). Der konservative 5s-Client-Default
# (infra/http.py) reisst dann intermittierend -> ReadTimeout -> Breaker oeffnet
# -> ALLE ParkenDD-Staedte upstream_unavailable. Hier explizit pro Request
# ueberschrieben (T-03-03, Overpass-Muster), ohne den Default fuer schnelle
# Quellen zu lockern.
_PARKENDD_TIMEOUT = httpx.Timeout(connect=2.0, read=15.0, write=5.0, pool=1.0)

# InfraNode-Slug -> ParkenDD-Stadt-ID (Pfadsegment). NUR die 13 Städte, deren
# Parkdaten-Ursprung eine OFFENE Standardlizenz führt (Lizenz-Recherche je Ursprung
# 2026-06-23, Owner-Entscheidung: keine Tier-B/C-/NC-Auslieferung). Die übrigen 9
# ParkenDD-Städte wurden bewusst ENTFERNT (-> automatisch not_covered): bonn ist
# CC BY-NC (kommerziell verboten!), hanau/ingolstadt/nuernberg proprietaer/
# zugangsbeschränkt, luebeck/magdeburg/mannheim/regensburg/wiesbaden ohne
# auffindbare Lizenz. Eine neue Stadt nur ergänzen, NACHDEM ihre Lizenz am
# Ursprung als offen verifiziert + in ``_PARKENDD_LICENSE`` (mappers/parkendd.py)
# eingetragen wurde.
PARKENDD_CITIES: dict[str, str] = {
    "aachen": "Aachen",
    "dortmund": "Dortmund",
    "dresden": "Dresden",
    "freiburg-im-breisgau": "Freiburg",
    "hamburg": "Hamburg",
    "heidelberg": "Heidelberg",
    "heilbronn": "Heilbronn",
    "kaiserslautern": "Kaiserslautern",
    "karlsruhe": "Karlsruhe",
    "koeln": "Koeln",
    "muenster": "Muenster",
    "oldenburg": "Oldenburg",
    "ulm": "Ulm",
}


async def fetch_parkendd(
    http: httpx.AsyncClient,
    *,
    slug: str,
    lat: float,
    lon: float,
    radius_km: float = 30.0,
) -> dict:
    """Holt die Live-Parkhaus-Belegung einer Stadt von ParkenDD.

    GET ``{_BASE}/{city_id}`` (city_id aus ``PARKENDD_CITIES[slug]``), dann je Lot
    ein schlankes dict (Name, Adresse, Koordinaten, frei/gesamt, Zustand, Typ).
    ``resp.raise_for_status()`` (5xx -> Fassade STALE-ON-ERROR). Felder defensiv.

    ``lat``/``lon``/``radius_km`` sind vertragskonform Teil der Signatur (alle
    Stadt-Adapter teilen sie), werden hier aber nicht zur Filterung genutzt
    (ParkenDD liefert den kompletten Stadt-Datensatz).

    Rückgabe-Keys (exakt das, was ``map_parkendd`` erwartet): ``slug``,
    ``facilities`` und ``as_of`` (Datenstand ISO-String oder None).

    Staleness-Guard: ist ``last_updated`` aelter als ``_MAX_AS_OF_AGE``
    (eingefrorener Upstream, siehe Modul-Kommentar), kommt ``facilities=[]``
    zurueck -> die Route liefert ehrlich ``no_data`` statt einer Jahre alten
    "Live"-Belegung. ``as_of`` bleibt zur Diagnose erhalten.
    """
    city_id = PARKENDD_CITIES[slug]
    resp = await http.get(f"{_BASE}/{city_id}", timeout=_PARKENDD_TIMEOUT)
    resp.raise_for_status()

    body = resp.json()
    lots = body.get("lots", []) if isinstance(body, dict) else []
    as_of = body.get("last_updated") if isinstance(body, dict) else None

    if _is_frozen(as_of):
        log.info("parkendd_frozen_upstream", slug=slug, as_of=as_of)
        return {"slug": slug, "facilities": [], "as_of": as_of}

    facilities: list[dict] = []
    for lot in lots:
        if not isinstance(lot, dict):
            continue
        coords = lot.get("coords") or {}
        try:
            f_lat = float(coords["lat"]) if coords.get("lat") is not None else None
            f_lon = float(coords["lng"]) if coords.get("lng") is not None else None
        except (TypeError, ValueError):
            f_lat = f_lon = None
        # H8 (Null-Regel): free:-1 zusammen mit state nodata/closed ist ein
        # Kein-Daten-Sentinel von ParkenDD, keine echte Belegung. Als None
        # ausweisen statt eine irreführende negative Zahl durchzureichen.
        state = lot.get("state")
        free = lot.get("free")
        total = lot.get("total")
        if (
            (isinstance(free, (int, float)) and free < 0)
            or state
            in {
                "nodata",
                "closed",
            }
            or (
                isinstance(free, (int, float))
                and isinstance(total, (int, float))
                and total > 0
                and free > total
            )
        ):
            free = None
        facilities.append(
            {
                "name": lot.get("name"),
                "address": lot.get("address"),
                "lat": f_lat,
                "lon": f_lon,
                "free": free,
                "total": total,
                "state": state,
                "lot_type": lot.get("lot_type"),
            }
        )

    return {"slug": slug, "facilities": facilities, "as_of": as_of}
