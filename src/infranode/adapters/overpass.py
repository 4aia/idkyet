"""OSM-POI-/Feature-Tag-Specs (DATA-04, Tier B copyleft).

Seit der Overpass-Ablösung (Precompute) gibt es KEINEN Live-Overpass-Adapter mehr:
die Routen (``cities.city_pois`` / ``_osm_feature_response``) lesen read-only aus
dem ``osm_pois``-Store, und der Batch-Ingest (``ingest.osm_pois``) füllt ihn offline
aus dem Geofabrik-Deutschland-Extrakt. Damit entfällt die Fair-Use-/Rate-Limit-
Abhängigkeit einer fremden Overpass-Instanz.

Dieses Modul ist die EINE Quelle der Wahrheit für die abgedeckten POI-/Feature-
Typen und ihre OSM-Tag-Selektoren. Sowohl der Ingest (über
``ingest.osm_poi_tags``, der hieraus ``match_poi_types`` ableitet) als auch die
Routen (Whitelist-Validierung ``_ALLOWED_TYPES`` und Extra-Tags ``_OSM_FEATURES``)
importieren dieselben Definitionen: Ingest und Auslieferung liefern damit exakt
dieselben Datenarten (kein Drift).

Sicherheit (T-05-09 Injection): Die POI-/Feature-Schlüssel sind eine feste
Whitelist. Roher User-Input (``?type=``) wird gegen ``_ALLOWED_TYPES`` geprüft
(unbekannt -> 422), bevor er in eine Store-Query fließt (die zudem
?-parametrisiert bindet); die Feature-Schlüssel sind interne Literale.
"""

from __future__ import annotations

from typing import NamedTuple

# Typ-Whitelist: jeder erlaubte ``poi_type`` mappt auf ein festes ``amenity``-Tag.
# Die Route validiert ``?type=`` hiergegen (unbekannt -> 422); der Ingest ordnet
# OSM-Elemente über denselben Tag-Vergleich zu (``osm_poi_tags.match_poi_types``).
_ALLOWED_TYPES: dict[str, str] = {
    "hospital": "hospital",
    "school": "school",
    "pharmacy": "pharmacy",
    "restaurant": "restaurant",
    "police": "police",
    "kindergarten": "kindergarten",
}


class _Feature(NamedTuple):
    """Definition einer OSM-Feature-Datenart (DATA-OSM, Tier B copyleft).

    ``groups`` ist eine Liste von Selektor-Gruppen; jede Gruppe ist eine Liste von
    ``(key, value)``-Tags, die innerhalb EINER Gruppe UND-verknüpft werden (z.B.
    ``amenity=recycling`` + ``recycling_type=centre``). Mehrere Gruppen bilden eine
    Vereinigung (erfüllt EINE Gruppe, zählt das Feature als Treffer). ``extra_tags``
    nennt OSM-Tag-Schlüssel, die über name/lat/lon hinaus je Element ausgeliefert
    werden (z.B. ``collection_times`` am Briefkasten, ``opening_hours``).
    """

    groups: tuple[tuple[tuple[str, str], ...], ...]
    extra_tags: tuple[str, ...]


# Feature-Whitelist: jeder Feature-Schlüssel mappt auf feste, hartkodierte Tag-
# Selektoren. Die Schlüssel sind zugleich die letzten Pfadsegmente der dedizierten
# Endpunkte (``/cities/{slug}/<feature>``) und die Store-``poi_type``-Werte.
_OSM_FEATURES: dict[str, _Feature] = {
    "playgrounds": _Feature(((("leisure", "playground"),),), ()),
    "drinking-water": _Feature(((("amenity", "drinking_water"),),), ()),
    # Oeffentliche Toiletten inkl. Barrierefreiheits-Tags (USP): wheelchair +
    # changing_table je Element, plus fee/access/opening_hours/unisex.
    "public-toilets": _Feature(
        ((("amenity", "toilets"),),),
        ("wheelchair", "changing_table", "fee", "access", "opening_hours", "unisex"),
    ),
    "markets": _Feature(((("amenity", "marketplace"),),), ("opening_hours",)),
    "parcel-lockers": _Feature(
        ((("amenity", "parcel_locker"),),), ("operator", "brand")
    ),
    "post-offices": _Feature(
        ((("amenity", "post_office"),),), ("opening_hours", "operator")
    ),
    "post-boxes": _Feature(((("amenity", "post_box"),),), ("collection_times",)),
    "public-wifi": _Feature(((("internet_access", "wlan"),),), ("operator",)),
    "recycling-centres": _Feature(
        ((("amenity", "recycling"), ("recycling_type", "centre")),),
        ("opening_hours",),
    ),
    "government-offices": _Feature(
        ((("office", "government"),), (("amenity", "townhall"),)),
        ("government", "operator"),
    ),
    "education": _Feature(
        (
            (("amenity", "school"),),
            (("amenity", "college"),),
            (("amenity", "university"),),
            (("amenity", "kindergarten"),),
        ),
        ("operator",),
    ),
}
