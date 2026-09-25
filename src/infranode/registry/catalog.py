"""Statischer Katalog aller Stadt-Datenarten (Discovery-Schicht für /overview).

Owner-Wunsch (2026-06-24): MCP-Agenten und Endnutzer sollen auf einen Blick sehen,
wie VIELE Datenarten es pro Stadt gibt, nicht nur das meistgenutzte Wetter. Dieser
Katalog ist die EINZIGE Quelle der Datenart-Labels + zugehöriger MCP-Tool-Namen
für den ``GET /cities/{slug}/overview``-Endpunkt.

Reine statische Metadaten (keine Upstream-Calls). Die Verfügbarkeit je Stadt wird
zur Laufzeit günstig aus ``registry.coverage`` abgeleitet. Eine Assertion im Test
``tests/integration/test_city_overview.py`` hält die Schlüssel deckungsgleich mit
der MCP-Allowlist (``mcp.client.ALLOWED_RESOURCES``), damit der Katalog beim
Hinzufügen einer neuen Datenart nicht still zurückfällt.
"""

from __future__ import annotations

from typing import NamedTuple


class DataType(NamedTuple):
    """Eine Stadt-Datenart für den Overview-Katalog.

    ``key`` ist das letzte Pfadsegment (``/cities/{slug}/<key>``) und zugleich der
    Coverage-Schlüssel (``registry.coverage.is_covered``). ``tool`` ist der Name
    des zugehörigen MCP-Tools, damit ein Agent direkt weiterspringen kann.
    """

    key: str
    tool: str
    label: str
    label_en: str


# Genau die City-Sub-Ressourcen aus ``mcp.client.ALLOWED_RESOURCES`` (Test hält
# die Mengen deckungsgleich). Labels mit echten Umlauten (deutsche Schreibweise).
CITY_DATA_CATALOG: tuple[DataType, ...] = (
    DataType("base", "get_city", "Basisdaten", "Base data"),
    DataType("weather", "weather", "Wetter", "Weather"),
    DataType(
        "weather-warnings", "weather_warnings", "Wetterwarnungen", "Weather warnings"
    ),
    # Quick-260705-ufv: BBK NINA Bevoelkerungsschutz-Warnungen je Stadt (keylos,
    # ARS-basiert, Voll-Abdeckung). Kein Eintrag in _NAMED_TOOLS -> laeuft ueber
    # get_city_resource. Label mit korrektem Umlaut, key/tool ASCII.
    DataType(
        "civil-protection-warnings",
        "civil_protection_warnings",
        "Bevölkerungsschutz-Warnungen",
        "Civil protection warnings",
    ),
    DataType("pollen-uv", "pollen_uv", "Pollen & UV-Index", "Pollen & UV index"),
    DataType("fire-danger", "fire_danger", "Waldbrandgefahr", "Wildfire danger"),
    DataType(
        "bathing-water",
        "bathing_water",
        "Badegewässerqualität",
        "Bathing water quality",
    ),
    DataType(
        "hospitals-atlas",
        "hospitals_atlas",
        "Krankenhausatlas",
        "Hospital atlas",
    ),
    DataType(
        "station-facilities",
        "station_facilities",
        "Aufzüge & Rolltreppen (Bahnhof)",
        "Elevators & escalators (station)",
    ),
    DataType("air", "air_quality_live", "Luftqualität (live)", "Air quality (live)"),
    DataType(
        "air-uba", "air_quality", "Luftqualität (amtlich)", "Air quality (official)"
    ),
    DataType(
        "station-departures",
        "station_departures",
        "Bahn-Abfahrten (Hbf)",
        "Train departures (main station)",
    ),
    DataType(
        "station-arrivals",
        "station_arrivals",
        "Bahn-Ankünfte (Hbf)",
        "Train arrivals (main station)",
    ),
    DataType("stations", "stations", "Bahnhöfe", "Railway stations"),
    DataType("traffic", "traffic", "Autobahn-Verkehr", "Motorway traffic"),
    DataType(
        "road-events",
        "road_events",
        "Innerstädtische Baustellen",
        "Inner-city roadworks",
    ),
    DataType("webcams", "webcams", "Verkehrs-Webcams", "Traffic webcams"),
    # DATA-42: eRound-Live-Ladebelegung je Stadt (AFIR DATEX-II V3, CC0). Join
    # aus Geo-Map (statischer Vollbestand) + akkumulierten Belegungs-Deltas.
    DataType(
        "charging-status",
        "charging_status",
        "Ladesäulen-Belegung (live)",
        "EV charging occupancy (live)",
    ),
    DataType("parking", "parking", "Parkhäuser", "Car parks"),
    DataType("fuel-prices", "fuel_prices", "Spritpreise", "Fuel prices"),
    DataType("sharing", "sharing", "Bike- & Scooter-Sharing", "Bike & scooter sharing"),
    DataType("health", "health", "Krankenhäuser", "Hospitals"),
    DataType("water-level", "water_level", "Pegelstände", "Water levels"),
    DataType("flood", "flood", "Hochwasserwarnungen", "Flood warnings"),
    DataType("demographics", "demographics", "Demografie", "Demographics"),
    DataType("unemployment", "unemployment", "Arbeitslosigkeit", "Unemployment"),
    DataType(
        "tourism", "tourism", "Tourismus (Übernachtungen)", "Tourism (overnight stays)"
    ),
    DataType("construction", "construction", "Baugenehmigungen", "Building permits"),
    DataType("power-load", "power_load", "Netzlast (Strom)", "Grid load (electricity)"),
    DataType(
        "power-price", "power_price", "Strom-Börsenpreis", "Day-ahead power price"
    ),
    DataType(
        "solar", "solar", "Solar-Einstrahlung & Ertrag", "Solar irradiation & yield"
    ),
    DataType("land-values", "land_values", "Bodenrichtwerte", "Land values"),
    DataType("events", "events", "Veranstaltungen", "Public events"),
    # DATA-OSM-Tier-2: Denkmallisten je Bundesland (Land-WFS, coverage-gated).
    DataType("heritage", "heritage", "Denkmäler", "Heritage monuments"),
    # DATA-OSM-Tier-2: Baumkataster je Stadt (kommunaler WFS, coverage-gated).
    DataType("tree-cadastre", "tree_cadastre", "Baumkataster", "Tree cadastre"),
    # DATA-OSM-Tier-2: Einwohnerdichte aus dem Zensus-2022-100m-Gitter (alle Städte).
    DataType(
        "population-density",
        "population_density",
        "Einwohnerdichte",
        "Population density",
    ),
    # TENDER-01/05: öffentliche Auftragsvergabe (oeffentlichevergabe.de, CC0 = Tier A).
    # key/tool ASCII (Pfadsegment + MCP-Tool), Label mit korrektem Umlaut.
    DataType(
        "public-tenders",
        "public_tenders",
        "Öffentliche Auftragsvergabe",
        "Public procurement",
    ),
    # DATA-40: kommunale Radzähl-Open-Data je Stadt (Dauerzählstellen, Tier A,
    # Teilabdeckung muenchen/leipzig/hamburg/berlin/stuttgart). key/tool ASCII,
    # Label mit korrektem Umlaut. NICHT das sharing-Tool (GBFS-Leihfahrzeuge).
    DataType(
        "bike-counts",
        "bike_counts",
        "Radzählstellen",
        "Bike counters",
    ),
    # Quick-260705-jgt: Behoerden-Wartezeiten je Stadt (live, keylos, Tier A,
    # Teilabdeckung nur koeln). key/tool ASCII (Pfadsegment), Label mit korrektem
    # Umlaut. Kein Eintrag in _NAMED_TOOLS -> laeuft ueber get_city_resource.
    DataType(
        "office-wait-times",
        "office_wait_times",
        "Behörden-Wartezeiten (live)",
        "Government office wait times (live)",
    ),
    # Quick-260708-tsv: kommunale Ratsinformationen (OParl "Paper" = Vorlagen,
    # Anträge, Beschlüsse) je Stadt, Tier A, Teilabdeckung (5 lizenzgeklärte
    # Städte). key/tool ASCII (Pfadsegment), Label mit korrektem Umlaut. Kein
    # Eintrag in _NAMED_TOOLS -> läuft über get_city_resource.
    DataType(
        "council-papers",
        "get_city_resource",
        "Ratsinformationen",
        "Council papers",
    ),
    # Quick-260729-muc: ruhender Verkehr je Stadt (Tier A, keylos, Teilabdeckung
    # nur muenchen). key/tool ASCII (Pfadsegment), Label mit korrektem Umlaut.
    # Kein Eintrag in _NAMED_TOOLS -> laeuft ueber get_city_resource.
    DataType(
        "parking-onstreet",
        "get_city_resource",
        "Strassenparkraum",
        "On-street parking",
    ),
    DataType(
        "park-and-ride",
        "get_city_resource",
        "P+R- und B+R-Anlagen",
        "Park & ride facilities",
    ),
    DataType(
        "mobility-points",
        "get_city_resource",
        "Mobilitaetspunkte",
        "Mobility points",
    ),
    DataType(
        "bike-parking",
        "get_city_resource",
        "Radparken",
        "Bike parking",
    ),
)

# MCP-TOOL-KONSOLIDIERUNG 2026-07-02: Der Long-Tail läuft über EIN generisches
# Tool ``get_city_resource(slug, resource=<key>)``; nur wenige Datenarten
# behalten ein namentliches Tool. Statt alle Einträge oben umzuschreiben (und
# jeden künftigen Eintrag daran zu erinnern), wird die Tool-Zuordnung hier
# ABGELEITET: die historischen ``tool``-Werte in den Literalen oben sind damit
# nur noch Dokumentation; maßgeblich ist diese Ableitung. Neue Datenarten
# zeigen automatisch auf get_city_resource. Der Overview-/Katalog-Konsument
# übergibt bei get_city_resource den ``type``-Schlüssel als resource-Argument
# (Hinweis steht in der infranode://catalog-Note und den Server-Instructions).
_NAMED_TOOLS: dict[str, str] = {
    "base": "get_city",
    "overview": "get_city_overview",
    "weather": "weather",
    "air-uba": "air_quality",
}

CITY_DATA_CATALOG = tuple(
    dt._replace(tool=_NAMED_TOOLS.get(dt.key, "get_city_resource"))
    for dt in CITY_DATA_CATALOG
)
