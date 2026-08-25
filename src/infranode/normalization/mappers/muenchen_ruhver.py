"""Reine Muenchen-Mapper fuer den ruhenden Verkehr (Quick-260729-muc, Tier A).

Uebersetzt die rohen Adapter-dicts aus ``adapters/muenchen_ruhver.py``
deterministisch in ``CanonicalRecord``s mit ``ParkingOnStreetPayload``,
``ParkAndRidePayload`` und ``MobilityPointPayload``. Hier liegt die gesamte
Normalisierungs-Logik (Best-Practice #6, eine getestete Quelle der Wahrheit):
Aggregation der 13.657 Parkseiten, Grad-Minuten-Sekunden nach Dezimalgrad,
deutsche Dezimalkommas und Euro-Betraege, "Ja"/"Nein" nach bool und deutsche
Datumsangaben nach ISO.

Die Funktionen sind rein: kein HTTP, keine Log-Aufrufe, keine Systemuhr.
``retrieved_at`` wird keyword-only injiziert, damit Tests deterministisch bleiben.

Lizenz: alle Quellen stehen unter der Datenlizenz Deutschland Namensnennung 2.0
(``license_id=DL_DE_BY_2_0``, ``license_tier=A``). Die WFS-Layer des
Mobilitaetsreferats tragen die wortgenaue Attribution "Landeshauptstadt
Muenchen" (mit Umlaut, siehe Konstante), die drei CKAN-Pakete der P+R-Anlagen
tragen "P+R Park & Ride GmbH Muenchen" , beide VERBATIM identisch zu
DATA-LICENSES.md und zur Quellen-Registry (Lizenz-Drift-Gate).

Zero-Trust: fehlende, leere oder unparsebare Felder werden zu ``None`` bzw.
uebersprungen, nie zu einem Fehler. Die Eintraege tragen ihre Koordinaten je
Objekt, daher record-level ``geo=None`` und ``observed_at=None`` (Stammdaten
ohne Messzeitpunkt).
"""

from __future__ import annotations

import re
from datetime import datetime

from infranode.normalization import (
    Attribution,
    BikeParkingPayload,
    CanonicalRecord,
    LicenseId,
    LicenseTier,
    MobilityPointPayload,
    ParkAndRidePayload,
    ParkingOnStreetPayload,
    SourceId,
)

_DL_DE_BY_URL = "https://www.govdata.de/dl-de/by-2-0"

# Wortgenaue Attributionen (VERBATIM identisch zu DATA-LICENSES.md und
# registry/source_specs.py; das Lizenz-Gate vergleicht Zeichen fuer Zeichen).
ATTRIBUTION_CITY = "Landeshauptstadt München"
ATTRIBUTION_PR = "P+R Park & Ride GmbH München"

# [VERIFIED 2026-07-29] Zeitscheiben der P+R-Belegungsprognose. Die CSV-Spalten
# heissen ``<tag>_<slot>_uhr`` mit tag in wt/sa/so.
_FORECAST_SLOTS = (
    "06-07",
    "07-08",
    "08-09",
    "09-10",
    "10-12",
    "12-14",
    "14-16",
    "16-18",
    "18-20",
    "20-06",
)
_FORECAST_DAYS = {"weekday": "wt", "saturday": "sa", "sunday": "so"}

# Ampel-Stufen der Prognose auf englische Werte (API-Konvention) abgebildet.
# "gruen" wird mitgelesen, falls der Datengeber die ASCII-Schreibweise nutzt.
_FORECAST_LEVELS = {
    "grün": "green",
    "gruen": "green",
    "gelb": "yellow",
    "rot": "red",
}

# Grad-Minuten-Sekunden wie ``48°05'51.0"N`` ([VERIFIED 2026-07-29] Format der
# beiden P+R-CSVs; Hoch- und Zollzeichen variieren, daher optional gematcht).
_DMS_RE = re.compile(
    r"(?P<deg>\d+)\s*°\s*(?P<min>\d+)\s*'\s*(?P<sec>[\d.,]+)\s*[\"'']?\s*"
    r"(?P<hemi>[NSEWO])",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
_DATE_RE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")


def _text(value: object) -> str | None:
    """Getrimmter Text oder ``None`` (leer, Platzhalter "--" und "-" inklusive).

    Zahlen werden mitgenommen und zu Text: dieselbe Angabe kommt je Format als
    String (CSV) oder als Zahl (GeoJSON) an, z. B. der Stadtbezirk als ``"8"``
    bzw. ``8``. Ohne diese Umwandlung fiele das Feld beim GeoJSON-Weg still auf
    ``None`` (2026-07-29 im Live-Smoke aufgefallen). ``bool`` bleibt ausgenommen,
    dafuer ist ``_bool`` zustaendig.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped or stripped in {"-", "--"}:
        return None
    return stripped


def _int(value: object) -> int | None:
    """Erste Ganzzahl im Wert oder ``None``."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = _text(value)
    if text is None:
        return None
    match = _NUMBER_RE.search(text.replace(".", ""))
    if match is None:
        return None
    try:
        return int(float(match.group(0).replace(",", ".")))
    except ValueError:
        return None


def _decimal(value: object) -> float | None:
    """Erste Dezimalzahl (deutsches Komma erlaubt) oder ``None``.

    Traegt der Wert mehrere Zahlen (z. B. "P+R Tarif: 1,50 EUR (1. Tag)"), wird
    die erste genommen; das ist bei den Preisspalten der Einzelpreis.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    text = _text(value)
    if text is None:
        return None
    match = _NUMBER_RE.search(text)
    if match is None:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def _bool(value: object) -> bool | None:
    """ "Ja"/"Nein" (auch "x" als Ja-Markierung) nach bool, sonst ``None``."""
    if isinstance(value, bool):
        return value
    text = _text(value)
    if text is None:
        return None
    lowered = text.lower()
    if lowered in {"ja", "x", "true", "1"}:
        return True
    if lowered in {"nein", "false", "0"}:
        return False
    return None


def _iso_date(value: object) -> str | None:
    """``TT.MM.JJJJ`` nach ``JJJJ-MM-TT``; alles andere -> ``None``.

    Auch das kompakte ``JJJJMMTT`` der WFS-Bearbeitungsdaten wird erkannt.
    """
    text = _text(value)
    if text is None:
        return None
    match = _DATE_RE.match(text)
    if match is not None:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    if len(text) == 8 and text.isdigit():
        return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"
    return None


def _dms(value: object) -> float | None:
    """Grad-Minuten-Sekunden nach Dezimalgrad; Nicht-DMS-Werte als Dezimalzahl.

    Suedliche/westliche Hemisphaere wird negativ. Ein Wert ohne Gradzeichen wird
    als bereits dezimale Koordinate gelesen, damit ein Formatwechsel des
    Datengebers nicht still zu ``None`` fuehrt.
    """
    text = _text(value)
    if text is None:
        return None
    match = _DMS_RE.search(text)
    if match is None:
        return _decimal(text)
    try:
        degrees = float(match.group("deg"))
        minutes = float(match.group("min"))
        seconds = float(match.group("sec").replace(",", "."))
    except ValueError:
        return None
    decimal = degrees + minutes / 60.0 + seconds / 3600.0
    if match.group("hemi").upper() in {"S", "W"}:
        decimal = -decimal
    return round(decimal, 7)


def _marker(row: dict, *keys: str) -> bool | None:
    """Marker-Spalte nach bool: "x" = ja, LEER = nein, fehlende Spalte = ``None``.

    Unterscheidet sich bewusst von ``_bool``: in einer Marker-Spalte (B+R-Liste:
    ``bei_p+r_anlage``) bedeutet der leere Wert "nein", nicht "unbekannt". Fehlt
    die Spalte dagegen ganz, ist die Aussage wirklich unbekannt -> ``None``.
    """
    for key in keys:
        if key in row:
            return _bool(row[key]) or False
    return None


def _pick(row: dict, *keys: str) -> object:
    """Erster vorhandener Schluessel aus ``keys`` (Schreibweisen-Varianten)."""
    for key in keys:
        if key in row:
            return row[key]
    return None


def _sum(values: list[int | None]) -> int | None:
    """Summe der nicht-``None``-Werte; nur ``None``-Werte -> ``None``."""
    known = [v for v in values if v is not None]
    return sum(known) if known else None


def map_muenchen_parking_onstreet(
    raw: dict,
    *,
    retrieved_at: datetime,
    ags: str | None = None,
    wikidata_qid: str | None = None,
) -> CanonicalRecord:
    """Bildet den Muenchner Strassenparkraum auf einen ``CanonicalRecord`` ab.

    Aggregiert die Parkseiten (ein Segment = ein Strassenabschnitt mit
    Stellplatzanzahl und Parkregelung) auf drei Sichten: je Regelungsgruppe, je
    Strasse und je Parkraummanagementgebiet. Die Gebiets-Sicht wird mit den
    Stammdaten des PRM-Layers (Massnahme, Status, Ueberwachung, Eroeffnung)
    zusammengefuehrt. Behindertenparkplaetze und Halteflaechen zum Laden und
    Liefern wandern als Punktlisten mit Koordinate in den Payload.

    Die Rohsegmente selbst werden NICHT ausgeliefert (13.657 Stueck); die drei
    Aggregate plus die Gesamtsummen sind die nutzbare Sicht, der Rohbezug steht
    in DATA-LICENSES.md.
    """
    segments = [s for s in raw.get("segments") or [] if isinstance(s, dict)]

    by_group: dict[str, dict] = {}
    by_street: dict[str, dict] = {}
    by_zone: dict[str, dict] = {}
    total_spaces = 0

    for segment in segments:
        spaces = _int(segment.get("angebot")) or 0
        total_spaces += spaces

        group = _text(segment.get("parkregel_gruppe")) or "ohne Angabe"
        bucket = by_group.setdefault(
            group, {"regulation_group": group, "segment_count": 0, "spaces": 0}
        )
        bucket["segment_count"] += 1
        bucket["spaces"] += spaces

        street = _text(segment.get("strasse"))
        if street is not None:
            street_bucket = by_street.setdefault(
                street, {"street": street, "segment_count": 0, "spaces": 0}
            )
            street_bucket["segment_count"] += 1
            street_bucket["spaces"] += spaces

        zone = _text(segment.get("prm_name"))
        if zone is not None:
            zone_bucket = by_zone.setdefault(zone, {"segment_count": 0, "spaces": 0})
            zone_bucket["segment_count"] += 1
            zone_bucket["spaces"] += spaces

    zones: list[dict] = []
    for row in raw.get("zones") or []:
        if not isinstance(row, dict):
            continue
        name = _text(row.get("name"))
        if name is None:
            continue
        aggregate = by_zone.get(name, {})
        zones.append(
            {
                "name": name,
                "measure": _text(row.get("massnahme")),
                "status": _text(row.get("status")),
                "enforcement": _text(row.get("ueberwachung")),
                "opened": _iso_date(row.get("eroeffnung")),
                "segment_count": aggregate.get("segment_count"),
                "spaces": aggregate.get("spaces"),
            }
        )

    accessible_bays: list[dict] = []
    for row in raw.get("accessible") or []:
        if not isinstance(row, dict):
            continue
        accessible_bays.append(
            {
                "label": _text(row.get("bezeichnung")),
                "category": _text(row.get("kategorie")),
                "spaces": _int(row.get("anzahl_stellplaetze")),
                "permanently_available": _bool(row.get("dauerhaft_verfuegbar")),
                "status": _text(row.get("status")),
                "time_restriction": _text(row.get("zeitliche_einschraenkung")),
                "district": _text(row.get("stadtbezirk")),
                "post_code": _text(row.get("plz")),
                "lat": row.get("_lat"),
                "lon": row.get("_lon"),
            }
        )

    loading_zones: list[dict] = []
    for row in raw.get("loading") or []:
        if not isinstance(row, dict):
            continue
        loading_zones.append(
            {
                "spaces": _int(row.get("angebot")),
                "regulation": _text(row.get("parkregel_beschreibung")),
                "usage": _text(row.get("wirtschaftsverkehr")),
                "status": _text(row.get("status_bedeutung")),
                "lat": row.get("_lat"),
                "lon": row.get("_lon"),
            }
        )

    return CanonicalRecord(
        city_slug=raw["slug"],
        geo=None,
        observed_at=None,
        retrieved_at=retrieved_at,
        source=SourceId.MUENCHEN_PARKING_ONSTREET,
        license_id=LicenseId.DL_DE_BY_2_0,
        license_tier=LicenseTier.A,
        ags=ags,
        wikidata_qid=wikidata_qid,
        attribution=Attribution(
            text=ATTRIBUTION_CITY,
            license_url=_DL_DE_BY_URL,
        ),
        payload=ParkingOnStreetPayload(
            segment_count=len(segments),
            total_spaces=total_spaces if segments else None,
            zone_count=len(zones),
            accessible_bay_count=len(accessible_bays),
            accessible_spaces=_sum([b["spaces"] for b in accessible_bays]),
            loading_zone_count=len(loading_zones),
            loading_spaces=_sum([z["spaces"] for z in loading_zones]),
            by_regulation=sorted(
                by_group.values(), key=lambda b: (-b["spaces"], b["regulation_group"])
            ),
            by_street=sorted(by_street.values(), key=lambda b: b["street"]),
            zones=sorted(zones, key=lambda z: z["name"]),
            accessible_bays=accessible_bays,
            loading_zones=loading_zones,
        ),
    )


def _forecast_for(name: str | None, forecasts: dict[str, dict]) -> dict | None:
    """Liefert die Belegungsprognose einer Anlage (exakter Namens-Match)."""
    if name is None:
        return None
    return forecasts.get(name)


def map_muenchen_park_and_ride(
    raw: dict,
    *,
    retrieved_at: datetime,
    ags: str | None = None,
    wikidata_qid: str | None = None,
) -> CanonicalRecord:
    """Bildet P+R-, B+R-Anlagen und Belegungsprognose auf einen Record ab.

    Die Koordinaten der beiden CKAN-CSVs stehen in Grad-Minuten-Sekunden und
    werden nach Dezimalgrad gerechnet; Preise, Einfahrtshoehe und Stellplatz-
    zahlen werden aus den deutschen Zahlformaten geparst. Die Belegungsprognose
    (Ampelstufe je Zeitscheibe, getrennt fuer Werktag, Samstag und Sonntag) wird
    per exaktem Anlagennamen an die jeweilige Anlage geheftet; ohne Treffer bleibt
    ``occupancy_forecast`` ``None``.

    WICHTIG: Das ist eine PROGNOSE aus historischen Erfahrungswerten, KEINE
    Echtzeit-Belegung. Muenchen veroeffentlicht (Stand 2026-07-29) keine offene
    Echtzeit-Belegung fuer Parkhaeuser oder P+R-Anlagen.
    """
    forecasts: dict[str, dict] = {}
    for row in raw.get("forecast_rows") or []:
        if not isinstance(row, dict):
            continue
        name = _text(_pick(row, "p+r_anlage", "p+r-anlage", "anlage"))
        if name is None:
            continue
        per_day: dict[str, dict] = {}
        for day_key, prefix in _FORECAST_DAYS.items():
            slots = {}
            for slot in _FORECAST_SLOTS:
                value = _text(row.get(f"{prefix}_{slot}_uhr"))
                slots[slot] = (
                    _FORECAST_LEVELS.get(value.lower()) if value is not None else None
                )
            per_day[day_key] = slots
        forecasts[name] = per_day

    car_facilities: list[dict] = []
    for row in raw.get("car_rows") or []:
        if not isinstance(row, dict):
            continue
        name = _text(row.get("name_anlage"))
        car_facilities.append(
            {
                "name": name,
                "address": _text(row.get("adresse")),
                "lat": _dms(row.get("latitude")),
                "lon": _dms(row.get("longitude")),
                "spaces_total": _int(row.get("stellplaetze_gesamt")),
                "spaces_accessible": _int(
                    _pick(row, "stellplaetze_beh.", "stellplaetze_beh")
                ),
                "spaces_women": _int(row.get("stellplaetze_frauen")),
                "spaces_family": _int(row.get("stellplaetze_fam")),
                "spaces_electric": _int(row.get("stellplaetze_elektro")),
                "spaces_motorcycle": _int(row.get("stellplaetze_motorraeder")),
                "structure_type": _text(row.get("bauform")),
                "entrance_height_m": _decimal(row.get("einfahrtshoehe")),
                "barrier_operation": _text(row.get("schrankenbetrieb")),
                "max_duration": _text(row.get("hoechstparkdauer")),
                "price_single_eur": _decimal(
                    _pick(row, "parkpreis_einzel", "parkpreis_einzel_eur")
                ),
                "price_ten_trip_eur": _decimal(row.get("parkpreis_zehner_eur")),
                "price_month_eur": _decimal(row.get("parkpreis_monat_eur")),
                "price_year_eur": _decimal(row.get("parkpreis_jahr_eur")),
                "price_level": _int(row.get("preisstufe")),
                "transit_lines": _text(
                    _pick(row, "oepnv-anbindung", "oepnv_anbindung")
                ),
                "occupancy_forecast": _forecast_for(name, forecasts),
            }
        )

    bike_facilities: list[dict] = []
    for row in raw.get("bike_rows") or []:
        if not isinstance(row, dict):
            continue
        bike_facilities.append(
            {
                "name": _text(row.get("name_anlage")),
                "address": _text(row.get("adresse")),
                "lat": _dms(row.get("latitude")),
                "lon": _dms(row.get("longitude")),
                "spaces": _int(row.get("abstellplaetze")),
                "structure_type": _text(row.get("bauform")),
                "at_park_and_ride": _marker(row, "bei_p+r_anlage", "bei_p+r-anlage"),
                "transit_lines": _text(
                    _pick(row, "oepnv-anbindung", "oepnv_anbindung")
                ),
            }
        )

    return CanonicalRecord(
        city_slug=raw["slug"],
        geo=None,
        observed_at=None,
        retrieved_at=retrieved_at,
        source=SourceId.MUENCHEN_PARK_AND_RIDE,
        license_id=LicenseId.DL_DE_BY_2_0,
        license_tier=LicenseTier.A,
        ags=ags,
        wikidata_qid=wikidata_qid,
        attribution=Attribution(
            text=ATTRIBUTION_PR,
            license_url=_DL_DE_BY_URL,
        ),
        payload=ParkAndRidePayload(
            car_facility_count=len(car_facilities),
            car_spaces_total=_sum([f["spaces_total"] for f in car_facilities]),
            bike_facility_count=len(bike_facilities),
            bike_spaces_total=_sum([f["spaces"] for f in bike_facilities]),
            car_facilities=car_facilities,
            bike_facilities=bike_facilities,
        ),
    )


def _carsharing_area(row: dict, *, kind: str) -> dict:
    """Baut einen Carsharing-Parkflaechen-Eintrag (Flaeche -> Punkt)."""
    return {
        "name": _text(row.get("sonderparken_standortname")),
        "provider": _text(row.get("anbietername")),
        "kind": kind,
        "type_label": _text(row.get("sonderparken_typ_text")),
        "district": _text(row.get("stadtbezirk")),
        "in_service_since": _iso_date(row.get("realisierungsdatum")),
        "lat": row.get("_lat"),
        "lon": row.get("_lon"),
    }


def map_muenchen_mobility_points(
    raw: dict,
    *,
    retrieved_at: datetime,
    ags: str | None = None,
    wikidata_qid: str | None = None,
) -> CanonicalRecord:
    """Bildet Mobilitaetspunkte und Carsharing-Parkflaechen auf einen Record ab.

    Ein Mobilitaetspunkt buendelt Carsharing-Stellplaetze, Ladepunkte,
    Abstellflaechen fuer geteilte Mikromobilitaet und die Anbindung an Bus, Tram,
    U- und S-Bahn an einer Informationsstele. Die Carsharing-Parkflaechen kommen
    aus zwei Layern: ``general`` (alle in Muenchen registrierten Carsharing-
    Fahrzeuge) und ``station_based`` (nur die dem Anbieter vertraglich
    zugewiesenen Fahrzeuge).

    Das im Layer mitgelieferte Kuerzel ``ods_vorhanden`` wird bewusst NICHT
    uebernommen: der Datengeber dokumentiert die Bedeutung nicht, und eine
    geratene Feldsemantik waere schlechter als ihr Fehlen.
    """
    points: list[dict] = []
    for row in raw.get("points") or []:
        if not isinstance(row, dict):
            continue
        points.append(
            {
                "name": _text(row.get("name")),
                "address": _text(row.get("adresse")),
                "lat": row.get("_lat"),
                "lon": row.get("_lon"),
                "carsharing_spaces": _int(row.get("anz_stellpl_cs")),
                "taxi_spaces": _int(row.get("anz_stellpl_taxi")),
                "charging_points_ac": _int(row.get("anzahl_ladepunkte_ac")),
                "charging_points_dc": _int(row.get("anzahl_ladepunkte_dc")),
                "has_scooter_area": _bool(row.get("gaf_ts_vorhanden")),
                "has_bikeshare_area": _bool(row.get("gaf_bs_vorhanden")),
                "has_cargo_bike_area": _bool(row.get("gaf_ls_vorhanden")),
                "has_moped_area": _bool(row.get("gaf_ms_vorhanden")),
                "has_bike_service_station": _bool(
                    row.get("radservicestation_vorhanden")
                ),
                "has_bike_pump": _bool(row.get("radpumpe_vorhanden")),
                "near_bus": _bool(row.get("bus_vorhanden")),
                "near_tram": _bool(row.get("tram_vorhanden")),
                "near_subway": _bool(row.get("u_bahn_vorhanden")),
                "near_suburban_rail": _bool(row.get("s_bahn_vorhanden")),
                "updated": _iso_date(row.get("bearbeitung_datum")),
            }
        )

    carsharing_areas: list[dict] = [
        _carsharing_area(row, kind="general")
        for row in raw.get("carsharing_general") or []
        if isinstance(row, dict)
    ]
    carsharing_areas.extend(
        _carsharing_area(row, kind="station_based")
        for row in raw.get("carsharing_station") or []
        if isinstance(row, dict)
    )

    return CanonicalRecord(
        city_slug=raw["slug"],
        geo=None,
        observed_at=None,
        retrieved_at=retrieved_at,
        source=SourceId.MUENCHEN_MOBILITY_POINTS,
        license_id=LicenseId.DL_DE_BY_2_0,
        license_tier=LicenseTier.A,
        ags=ags,
        wikidata_qid=wikidata_qid,
        attribution=Attribution(
            text=ATTRIBUTION_CITY,
            license_url=_DL_DE_BY_URL,
        ),
        payload=MobilityPointPayload(
            point_count=len(points),
            carsharing_area_count=len(carsharing_areas),
            carsharing_spaces=_sum([p["carsharing_spaces"] for p in points]),
            points=points,
            carsharing_areas=carsharing_areas,
        ),
    )


# Status-Text der Quelle -> Zustandsklasse. [VERIFIED 2026-07-30] am echten Layer:
# "in Bestand / in Betrieb" 3.233, "abgebaut" 306, "in Planung / in Entwuf" 156
# (Tippfehler stammt aus der Quelle), "ausser Betrieb" 25. Klassifiziert wird
# ueber Teilzeichenketten, damit ein korrigierter Tippfehler oder ein Zusatz die
# Zuordnung nicht bricht.
_BIKE_STATUS_KEYS: tuple[tuple[str, str], ...] = (
    ("abgebaut", "removed"),
    ("planung", "planned"),
    ("entwurf", "planned"),
    ("entwuf", "planned"),
    ("ausser betrieb", "out_of_service"),
    ("außer betrieb", "out_of_service"),
    ("bestand", "in_service"),
    ("in betrieb", "in_service"),
)


def _bike_status(value: object) -> str | None:
    """Ordnet den Status-Text einer Anlage einer Zustandsklasse zu.

    Unbekannter oder fehlender Text -> ``None``. Die Anlage zaehlt dann NICHT in
    den Bestand: eine Anlage ohne belegbaren Status als Bestand zu buchen wuerde
    die Stellplatzsumme nach oben verfaelschen.
    """
    text = _text(value)
    if text is None:
        return None
    lowered = text.lower()
    # "ausser Betrieb" muss vor "in Betrieb" greifen, sonst gewinnt die
    # Teilzeichenkette "betrieb" die falsche Klasse.
    for needle, status in _BIKE_STATUS_KEYS:
        if needle in lowered:
            return status
    return None


def _bike_facility(row: dict) -> dict:
    """Normalisiert eine Zeile der beiden Radparken-Layer."""
    return {
        "location": _text(row.get("standort")),
        "spaces": _int(row.get("anzahl_stellplaetze")),
        "type": _text(row.get("typ_generalisiert")),
        "covered": _bool(row.get("ueberdacht")),
        "double_deck": _bool(row.get("doppelstock")),
        "lit": _bool(row.get("zusatzbeleuchtung")),
        # FREITEXT, kein Ja/Nein ([VERIFIED 2026-07-30]: 3.712 von 3.720 leer,
        # der Rest traegt Angaben wie "Werktags 9 - 23 Uhr" oder
        # "vom 01.04. mit 31.10."). Ueber _bool gelesen waeren alle acht echten
        # Faelle still zu None geworden und die Zaehlung haette 0 gemeldet.
        "time_limit": _text(row.get("zeitl_begrenzung")),
        "bike_and_ride": _bool(row.get("bike_and_ride")),
        "cargo_bike": _bool(row.get("lastenrad")),
        "status": _bike_status(row.get("status_bedeutung")),
    }


def _bike_totals(facilities: list[dict]) -> dict:
    """Summiert Anlagen und Stellplaetze einer Liste."""
    return {
        "facility_count": len(facilities),
        "spaces_total": _sum([f["spaces"] for f in facilities]),
    }


def map_muenchen_bike_parking(
    raw: dict,
    *,
    retrieved_at: datetime,
    ags: str | None = None,
    wikidata_qid: str | None = None,
) -> CanonicalRecord:
    """Bildet die Rad- und Lastenradabstellanlagen auf einen Record ab.

    Gezaehlt wird NUR der Bestand. Die Quelle fuehrt im selben Layer auch
    abgebaute, geplante und ausser Betrieb genommene Anlagen; ihre Stellplaetze
    mitzuzaehlen wuerde den heutigen Radparkraum deutlich zu hoch ausweisen
    ([VERIFIED 2026-07-30]: 47.518 Plaetze im Bestand gegen 55.369 ueber alle
    Zustaende, also rund 17 Prozent zu viel). Die anderen Zustaende stehen als
    eigene Zahlen daneben, statt sie zu verschweigen.

    Lastenradanlagen liegen in einem eigenen Layer und werden getrennt
    ausgewiesen: sie sind fuer andere Fahrzeuge ausgelegt, und eine gemeinsame
    Summe wuerde die Frage "wie viele Radstellplaetze hat die Stadt" verfaelschen.

    Die 3.720 Einzelanlagen werden nicht ausgeliefert (mehrere hundert Kilobyte),
    stattdessen Summen, Aggregate je Bauform und die zwanzig groessten Standorte.
    """
    bike = [
        _bike_facility(row) for row in raw.get("bike") or [] if isinstance(row, dict)
    ]
    cargo = [
        _bike_facility(row) for row in raw.get("cargo") or [] if isinstance(row, dict)
    ]

    in_service = [f for f in bike if f["status"] == "in_service"]
    planned = [f for f in bike if f["status"] == "planned"]
    removed = [f for f in bike if f["status"] == "removed"]
    out_of_service = [f for f in bike if f["status"] == "out_of_service"]

    by_type: dict[str, dict] = {}
    for facility in in_service:
        label = facility["type"] or "unbekannt"
        entry = by_type.setdefault(label, {"type": label, "facilities": 0, "spaces": 0})
        entry["facilities"] += 1
        entry["spaces"] += facility["spaces"] or 0

    bike_and_ride = [f for f in in_service if f["bike_and_ride"]]
    largest = sorted(in_service, key=lambda f: f["spaces"] or 0, reverse=True)[:20]
    cargo_in_service = [f for f in cargo if f["status"] == "in_service"]

    return CanonicalRecord(
        city_slug=raw["slug"],
        geo=None,
        observed_at=None,
        retrieved_at=retrieved_at,
        source=SourceId.MUENCHEN_BIKE_PARKING,
        license_id=LicenseId.DL_DE_BY_2_0,
        license_tier=LicenseTier.A,
        ags=ags,
        wikidata_qid=wikidata_qid,
        attribution=Attribution(
            text=ATTRIBUTION_CITY,
            license_url=_DL_DE_BY_URL,
        ),
        payload=BikeParkingPayload(
            facility_count=len(in_service),
            spaces_total=_sum([f["spaces"] for f in in_service]),
            covered_facilities=sum(1 for f in in_service if f["covered"]),
            double_deck_facilities=sum(1 for f in in_service if f["double_deck"]),
            lit_facilities=sum(1 for f in in_service if f["lit"]),
            time_limited_facilities=sum(1 for f in in_service if f["time_limit"]),
            bike_and_ride_facilities=len(bike_and_ride),
            bike_and_ride_spaces=_sum([f["spaces"] for f in bike_and_ride]),
            planned_facilities=len(planned),
            planned_spaces=_sum([f["spaces"] for f in planned]),
            removed_facilities=len(removed),
            out_of_service_facilities=len(out_of_service),
            by_type=sorted(by_type.values(), key=lambda e: e["spaces"], reverse=True),
            cargo_bike=_bike_totals(cargo_in_service),
            largest_facilities=largest,
        ),
    )
