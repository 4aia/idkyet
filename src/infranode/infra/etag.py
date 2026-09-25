"""ETag-/Cache-Control-Verträge (API-08): compute_etag + CACHE_TTL-Map.

``compute_etag`` baut einen stabilen ETag aus dem serialisierten Response-Body
(sha256-Idiom analog infra/cache.py:build_cache_key, hier über Body-Bytes). Der
ETag wird serverseitig berechnet; If-None-Match wird nur verglichen, nie als
Cache-Schlüssel verwendet (Cache-Poisoning-Schutz). Die TTL-Map liefert je
Ressource das Cache-Control-Fenster (Sekunden); ``default`` greift sonst.

Die ETag-/304-Middleware selbst (nur GET/200 cachen, nie Fehler-Envelopes) wird
in Wave 3 verdrahtet; hier stehen die importierbaren Helper-Verträge fest.
"""

from __future__ import annotations

import hashlib

# Cache-Control-TTL je Datenart (Sekunden). Die Datenart ist das LETZTE
# Pfadsegment (/api/v1/cities/<slug>/<datenart>), nicht das Bereichssegment
# ("cities"). Unbekannte Segmente (Stadt-Slug, Listen-Endpunkte, hier nicht
# gelistete Datenarten) fallen auf ``default`` zurück. Additiv erweiterbar ohne
# Logik-Änderung. Bewusst NICHT gelistet und damit auf dem kurzen default:
# Warnungen (weather-warnings, civil-protection-warnings), Semi-Live
# (charging-status, power-load/-price, fuel-prices, office-wait-times,
# bike-counts, station-departures/-arrivals) und "overview" (mischt
# einen Live-Snapshot ein) - diese dürfen nie lange stale sein.
DEFAULT_TTL = 300

# ~6 h: Stammdaten, Infrastruktur-POIs, Geo und amtliche Statistik. Ändern sich
# höchstens täglich (meist monatlich/jährlich); langes Fenster entlastet das
# Origin, ETag/304 hält die Revalidierung billig.
_LONG_TTL = 21600
_LONG_RESOURCES = frozenset(
    {
        "base",
        "demographics",
        "population-density",
        "solar",
        "heritage",
        "tree-cadastre",
        "hospitals-atlas",
        "station-facilities",
        "land-values",
        "unemployment",
        "tourism",
        "construction",
    }
)

# 30 min: Wetter/Umwelt, täglich/stündlich aktualisiert.
_MEDIUM_TTL = 1800
_MEDIUM_RESOURCES = frozenset(
    {
        "weather",
        "pollen-uv",
        "fire-danger",
        "bathing-water",
    }
)

# 10 min: Luftqualität (deprecated /cities-Aliase; die Live-Varianten unter
# /live sind ohnehin no-store).
_SHORT_TTL = 600
_SHORT_RESOURCES = frozenset({"air", "air-uba"})

CACHE_TTL = {
    **dict.fromkeys(_LONG_RESOURCES, _LONG_TTL),
    **dict.fromkeys(_MEDIUM_RESOURCES, _MEDIUM_TTL),
    **dict.fromkeys(_SHORT_RESOURCES, _SHORT_TTL),
    "default": DEFAULT_TTL,
}

# Ressourcen, die NIE am CDN/Browser zwischengespeichert werden dürfen ->
# "no-store". Echtzeit-Endpunkte unter /api/v1/live/* (Resource-Segment "live":
# HVV-Abfahrten, GTFS-RT-Transit, Dortmund-Parken, Koeln/Berlin-Live u.a.)
# liefern minütlich wechselnde Daten. Ohne no-store cached Cloudflare die
# Antwort bis zu seiner Browser-Cache-TTL (beobachtet: 4 h Override trotz
# origin max-age=300) und serviert Live-Daten massiv stale; ein transienter
# no_data-Zustand bliebe stundenlang eingefroren. no-store hält /live/
# cache-frei (Origin-Last bleibt klein, da der resiliente Redis-Cache davor
# liegt). Clients steuern ihren Poll-Takt über meta.refresh_seconds.
NO_STORE_RESOURCES = frozenset({"live", "track"})


def compute_etag(body: bytes) -> str:
    """ETag aus dem serialisierten Body: gequoteter sha256[:32]-Hex.

    Deterministisch über die rohen Response-Bytes (ORJSONResponse liefert
    bytes). Gleicher Body -> gleicher ETag -> If-None-Match-Match -> 304.
    """
    return '"' + hashlib.sha256(body).hexdigest()[:32] + '"'


def cache_control_for(resource: str | None = None, *, area: str | None = None) -> str:
    """Cache-Control-Wert je Datenart aus der CACHE_TTL-Map.

    ``resource`` ist die Datenart (letztes Pfadsegment); ``area`` das
    Bereichssegment (/api/v1/<area>/...), das nur über ``no-store`` entscheidet.
    Wählt die passende max-age-TTL ("public, max-age=<ttl>"); fällt auf
    ``default`` (300 s) zurück, wenn die Datenart nicht in CACHE_TTL steht. Der
    Wert ist additiv erweiterbar, ohne die Middleware-Logik zu ändern.

    Ist der Bereich (oder ersatzweise die Datenart) in ``NO_STORE_RESOURCES``
    (Echtzeit-Endpunkte /api/v1/live/*, /track), wird ``no-store`` geliefert,
    damit Cloudflare/Browser sie nicht zwischenspeichern (sonst werden
    Live-Daten bis zur CDN-Browser-TTL stale). Der no-store-Anker hängt am
    Bereich, nicht an der Datenart: /live/<stadt>/departures endet auf
    "departures", der Echtzeit-Charakter steckt allein in "live".
    """
    if area in NO_STORE_RESOURCES or resource in NO_STORE_RESOURCES:
        return "no-store"
    ttl = CACHE_TTL.get(resource or "default", CACHE_TTL["default"])
    # stale-while-revalidate + stale-if-error (Security-Härtung 2026-06-21):
    # Nach Ablauf der max-age liefert ein Shared Cache (Cloudflare) die Antwort
    # SOFORT weiter und revalidiert asynchron im Hintergrund -> kein Thundering
    # Herd aufs Origin bei populären Endpunkten (DoS-/Scraping-Last-Glättung).
    # stale-if-error hält die API bei Origin-Ueberlast/-Ausfall antwortfähig
    # (das CDN serviert die letzte gute Antwort statt eines Fehlers). Fenster =
    # ttl. Greift nur an einem Shared Cache; Browser ignorieren swr i. d. R.
    return f"public, max-age={ttl}, stale-while-revalidate={ttl}, stale-if-error={ttl}"
