"""Oeffentliche Per-City-Coverage-Karte der teilabgedeckten Endpunkte.

Ehrlichkeit statt leerer Versprechen (Owner-Entscheidung 2026-06-13): einige
Endpunkte decken nur kuratierte Städte ab. Früher lieferten sie für eine
nicht-abgedeckte Stadt ein leeres ``source_status="ok"`` (sieht aus wie "kein
Ereignis"), was die fehlende Abdeckung verschleiert. Stattdessen weisen die
Routen jetzt ``source_status="not_covered"`` aus (200, ``data: null``) und
nennen im meta-Block die abgedeckten Städte (``covered_cities``). ``not_covered``
ist klar unterscheidbar von ``no_data`` (Stadt abgedeckt, aktuell aber keine
Daten) und vom 404 (Stadt unbekannt).

Dieses Modul ist die EINZIGE Quelle der Wahrheit der Abdeckung und wird aus den
kuratierten Adapter-Stadt-Maps ABGELEITET (kein Duplizieren der Slug-Listen):
- ``flood``    -> ``adapters.lhp._CITY_PEGEL`` (kuratierte Pegel je Stadt)
- ``webcams``  -> ``adapters.autobahn._CITY_ROADS`` (kuratierte Autobahnen)
- ``traffic``  -> ``adapters.autobahn._CITY_ROADS`` (dieselbe Map wie webcams)
- ``road-events`` -> ``api.v1.cities.CONNECTOR_MAP`` (kuratierte Stadt-Connectoren)

Da ``CONNECTOR_MAP`` in ``cities.py`` lebt (mit fetch_fn/mapper-Tupeln) und
``cities.py`` dieses Modul importiert, wird die road-events-Liste hier gespiegelt
statt importiert (Zirkelimport-Vermeidung). Eine Modul-Assertion in ``cities.py``
sichert die Gleichheit beider Listen ab und fängt Drift beim Import hart ab.

NICHT teilabgedeckt (bewusst NICHT in dieser Karte):
- ``water-level``: Geo-Proximity ohne kuratierte Stadt-Map; liefert bei fehlender
  naher Station bereits ehrlich ``no_data`` (dynamisch, deutschlandweit an
  Bundeswasserstraßen).
- ``live/transit/*``: bundesweiter GTFS-RT-Feed ohne strukturelle Stadt-Grenze;
  ``no_data`` bei leerem Redis bleibt das ehrliche Verdict.
Alle übrigen city-/live-Endpunkte sind flächendeckend (84/84).
"""

from __future__ import annotations

from infranode.adapters.autobahn import _CITY_ROADS
from infranode.adapters.baumkataster import BAUM_WFS
from infranode.adapters.boris import BORIS_SHAPEFILE, BORIS_WFS
from infranode.adapters.denkmal import HERITAGE_WFS
from infranode.adapters.lhp import _CITY_PEGEL
from infranode.registry.cities import CITY_REGISTRY

# road-events: gespiegelt aus ``api.v1.cities.CONNECTOR_MAP`` (siehe Modul-Docstring).
# Die Assertion in cities.py hält diese Liste mit der CONNECTOR_MAP synchron.
_ROAD_EVENTS_CITIES: frozenset[str] = frozenset(
    {
        "berlin",
        "koeln",
        "hamburg",
        "muenchen",
        "stuttgart",
        "bremen",
        "dortmund",
        "dresden",
        "leipzig",
        "rostock",
    }
)

# sharing (DATA-33): gespiegelt aus ``api.v1.cities.GBFS_SYSTEMS`` (kuratierte
# Nextbike-GBFS-Systeme je Stadt). Wie bei road-events lebt die Quell-Map in
# cities.py (das dieses Modul importiert), daher wird die Slug-Menge hier
# gespiegelt und per Modul-Assertion in cities.py drift-synchron gehalten.
_SHARING_CITIES: frozenset[str] = frozenset(
    {
        "berlin",
        "muenchen",
        "koeln",
        "frankfurt-am-main",
        "duesseldorf",
        "dresden",
        "leipzig",
        "hannover",
        "nuernberg",
        "bremen",
        "braunschweig",
        "freiburg-im-breisgau",
        "karlsruhe",
        "aachen",
        "kassel",
        "wiesbaden",
        "oldenburg",
        "potsdam",
        "bielefeld",
        "moenchengladbach",
        "mannheim",
        "heidelberg",
        "ludwigshafen-am-rhein",
        "hanau",
        "leverkusen",
        "kiel",
    }
)

# station-departures/-arrivals (DATA-34/36): NICHT mehr teilabgedeckt. Die Haupt-
# Bahnhof-EVAs je Stadt werden aus dem StaDa-Katalog abgeleitet
# (api.v1.cities._resolve_city_station_evas) -> volle Abdeckung über alle 84
# Städte. Daher kein PARTIAL_COVERAGE-Eintrag (kein not_covered) mehr.

# land-values (DATA-35): BORIS ist pro Bundesland föderiert -> abgedeckt sind
# genau die Register-Städte, deren Bundesland (``state``) entweder einen offenen
# WFS (``BORIS_WFS``) ODER einen offenen Shapefile-Download (``BORIS_SHAPEFILE``,
# NW/ST) hat. Direkt aus beiden Maps + Register ABGELEITET (kein Duplizieren): ein
# neues Land erweitert die Abdeckung automatisch.
_BORIS_STATES = set(BORIS_WFS) | set(BORIS_SHAPEFILE)
_LAND_VALUES_CITIES: frozenset[str] = frozenset(
    c.slug for c in CITY_REGISTRY if c.state in _BORIS_STATES
)

# parking (DATA-40 / PARK-08): EIN Parking-Endpunkt je Stadt mit kuratierter
# Direktquelle. Diese Menge MUSS deckungsgleich zur ``PARKING_CONNECTORS``-Registry in
# api/v1/cities.py bleiben (der dortige Drift-Guard erzwingt es); eine neue Parkstadt
# wird in BEIDEN ergänzt. Quellen je Stadt: Stadt-OpenData-Direkt (dortmund/aachen/
# muenster/oldenburg/kaiserslautern/karlsruhe), MobiData BW ParkAPI (freiburg-im-
# breisgau/heidelberg/heilbronn/ulm), statischer CKAN-Katalog (muenchen), Mobilithek
# DATEX II (frankfurt-am-main/wuppertal/magdeburg/koeln, koeln seit 2026-07-23 direkt
# statt ParkenDD), Hamburg-Urban-Platform-WFS (hamburg) und der Übergangs-Aggregator
# für die noch nicht direkt angebundene Stadt (dresden, bis 25-08). Die frueheren DB-
# BahnPark-Staedte (statischer Katalog ohne Live-Call) sind mit dem Cleanup 260925
# entfernt (offline/precompute-only Quelle, keine per-Request-Live-API).
_PARKING_CITIES: frozenset[str] = frozenset(
    {
        "dortmund",
        "aachen",
        "muenster",
        "oldenburg",
        "kaiserslautern",
        "karlsruhe",
        "freiburg-im-breisgau",
        "heidelberg",
        "heilbronn",
        "ulm",
        "muenchen",
        "frankfurt-am-main",
        "wuppertal",
        "magdeburg",
        "dresden",
        "hamburg",
        "koeln",
    }
)

# bike-counts (DATA-40): kommunale Radzählstellen-Open-Data je Stadt (KEIN
# Eco-Counter: Lizenz ungeklärt, Owner-Entscheidung 2026-06-23). Jede Stadt eine
# eigene, am Ursprung lizenz-verifizierte Quelle. Wächst additiv je integrierter
# Stadt (muss synchron zu ``_resolve_bike_counts_connector`` in api/v1/cities.py
# bleiben).
_BIKE_COUNTS_CITIES: frozenset[str] = frozenset(
    {
        "muenchen",
        "leipzig",
        "hamburg",
        "berlin",
        "stuttgart",
        "koeln",
        "essen",
        "duesseldorf",
    }
)

# heritage (DATA-OSM-Tier-2): Denkmallisten sind LANDESsache -> föderiert per WFS
# (wie BORIS/solar-roofs). Abgedeckt sind die Register-Städte, deren Bundesland
# (``state``) einen verifizierten, offen lizenzierten Denkmal-WFS hat
# (``HERITAGE_WFS``). Ein neues Land erweitert die Abdeckung automatisch.
_HERITAGE_STATES = set(HERITAGE_WFS)
_HERITAGE_CITIES: frozenset[str] = frozenset(
    c.slug for c in CITY_REGISTRY if c.state in _HERITAGE_STATES
)

# tree-cadastre (DATA-OSM-Tier-2): Baumkataster sind kommunales Open Data -> per
# Stadt konfiguriert (``BAUM_WFS``). Abgedeckt sind genau die konfigurierten,
# verifiziert offen lizenzierten Städte. Eine neue Stadt erweitert automatisch.
_TREE_CADASTRE_CITIES: frozenset[str] = frozenset(BAUM_WFS)

# office-wait-times (Quick-260705-jgt): Behoerden-Wartezeiten live. Aktuell NUR
# Koeln abgedeckt (keyloser Direkt-Feed waiting-od.php); andere Staedte liefern
# ehrlich not_covered (200, kein 404). Waechst additiv je integrierter Stadt.
_OFFICE_WAIT_TIMES_CITIES: frozenset[str] = frozenset({"koeln"})

# Quick-260729-muc: ruhender Verkehr Muenchen. Drei Datenarten aus den offenen
# Quellen der Landeshauptstadt (WFS Mobilitaetsreferat + CKAN P+R GmbH). Aktuell
# NUR muenchen; andere Staedte liefern ehrlich not_covered (200, kein 404).
# Waechst additiv je integrierter Stadt.
_PARKING_ONSTREET_CITIES: frozenset[str] = frozenset({"muenchen"})
_PARK_AND_RIDE_CITIES: frozenset[str] = frozenset({"muenchen"})
_MOBILITY_POINT_CITIES: frozenset[str] = frozenset({"muenchen"})
_BIKE_PARKING_CITIES: frozenset[str] = frozenset({"muenchen"})

# council-papers (Quick-260708-tsv): kommunale Ratsinformationen (OParl) je Stadt.
# Teilabdeckung = die acht lizenzgeklärten Städte (fail-closed, KEINE weiteren).
# Deckungsgleich zu mappers.oparl.COVERED_COUNCIL_CITIES (dort Single Source of
# Truth für Route + Lizenz); hier als eigene Konstante gespiegelt, damit die
# coverage-Karte ohne Import-Zyklus lädt.
_COUNCIL_CITIES: frozenset[str] = frozenset(
    {
        "dresden",
        "koeln",
        "duesseldorf",
        "muenster",
        "leipzig",
        "magdeburg",
        "osnabrueck",
        "freiburg-im-breisgau",
    }
)

# Single source of truth: Endpunkt-Kennung -> abgedeckte Stadt-Slugs.
# Die Kennung entspricht dem letzten Pfadsegment der Route (``/cities/{slug}/<key>``).

PARTIAL_COVERAGE: dict[str, frozenset[str]] = {
    "flood": frozenset(_CITY_PEGEL),
    "webcams": frozenset(_CITY_ROADS),
    "traffic": frozenset(_CITY_ROADS),
    "road-events": _ROAD_EVENTS_CITIES,
    "sharing": _SHARING_CITIES,
    "land-values": _LAND_VALUES_CITIES,
    "parking": _PARKING_CITIES,
    "bike-counts": _BIKE_COUNTS_CITIES,
    "heritage": _HERITAGE_CITIES,
    "tree-cadastre": _TREE_CADASTRE_CITIES,
    "office-wait-times": _OFFICE_WAIT_TIMES_CITIES,
    "council-papers": _COUNCIL_CITIES,
    "parking-onstreet": _PARKING_ONSTREET_CITIES,
    "park-and-ride": _PARK_AND_RIDE_CITIES,
    "mobility-points": _MOBILITY_POINT_CITIES,
    "bike-parking": _BIKE_PARKING_CITIES,
}

# Drift-Schutz: die gespiegelte council-papers-Liste MUSS deckungsgleich mit der
# Single Source of Truth im Mapper sein (mappers.oparl importiert nichts aus
# diesem Modul -> kein Import-Zyklus). Fängt eine hier vergessene Stadt hart ab.
from infranode.normalization.mappers.oparl import (  # noqa: E402
    COVERED_COUNCIL_CITIES as _MAPPER_COUNCIL_CITIES,
)

if _COUNCIL_CITIES != _MAPPER_COUNCIL_CITIES:
    raise RuntimeError(
        "council-papers coverage drift: registry.coverage._COUNCIL_CITIES != "
        "mappers.oparl.COVERED_COUNCIL_CITIES"
    )


def is_covered(endpoint: str, slug: str) -> bool:
    """True, wenn ``slug`` für ``endpoint`` abgedeckt ist.

    Ein unbekannter ``endpoint`` (nicht teilabgedeckt -> flächendeckend) gilt
    immer als abgedeckt (fail-open für die fully-covered-Endpunkte, die diese
    Karte nie befragen).
    """
    covered = PARTIAL_COVERAGE.get(endpoint)
    if covered is None:
        return True
    return slug in covered


def covered_cities(endpoint: str) -> list[str]:
    """Sortierte Liste der für ``endpoint`` abgedeckten Stadt-Slugs.

    Für die meta.covered_cities-Ausweisung der ``not_covered``-Antwort. Leer für
    einen unbekannten (= flächendeckenden) Endpunkt.
    """
    return sorted(PARTIAL_COVERAGE.get(endpoint, frozenset()))
