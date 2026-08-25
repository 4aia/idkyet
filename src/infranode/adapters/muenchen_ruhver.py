"""Muenchen-Adapter fuer den ruhenden Verkehr (Parken, Quick-260729-muc).

Drei Fetcher fuer drei neue Datenarten, alle unter DL-DE/BY 2.0 (Tier A):

1. ``fetch_muenchen_parking_onstreet`` , Strassenparkraum aus vier WFS-Layern des
   Mobilitaetsreferats (``geoportal.muenchen.de``, GeoServer-Workspace
   ``mor_wfs``): Parkseiten (Stellplatzanzahl + Parkregelung je Strassen-
   abschnitt), Parkraummanagementgebiete, Behindertenparkplaetze und die
   Halteflaechen "Laden, Liefern, Leisten".
2. ``fetch_muenchen_park_and_ride`` , P+R- und B+R-Anlagen samt Belegungs-
   prognose aus drei CKAN-Paketen der P+R Park & Ride GmbH Muenchen auf
   ``opendata.muenchen.de``.
3. ``fetch_muenchen_mobility_points`` , Mobilitaetspunkte und die beiden
   Carsharing-Parkflaechen-Layer (allgemein + stationsbasiert) aus demselben WFS.

[VERIFIED 2026-07-29] per Live-Probe gegen beide Hosts: Layer-Namen, Feldnamen
und Groessenordnungen (Parkseiten 13.657 Segmente / 101.615 Stellplaetze,
Behindertenparkplaetze 557, PRM-Gebiete 82, Laden/Liefern 560, Mobilitaets-
punkte 120, Carsharing 711 allgemein + 199 stationsbasiert).

Groessen-Abwaegung: die Parkseiten werden als CSV mit ``propertyName``-Auswahl
geholt (nur die fuenf ausgewerteten Attribute, keine Geometrie) , das sind rund
700 KB statt mehrerer MB GeoJSON. Die Punkt-/Flaechen-Layer kommen als GeoJSON
mit ``srsName=EPSG:4326`` (ohne diesen Parameter liefert der GeoServer
EPSG:25832) und werden sofort auf einen repraesentativen Punkt reduziert.

Sicherheit (T-9-02 SSRF): Beide Hosts sind hartkodiert; die in CKAN Step 1
entdeckte Ressourcen-URL MUSS in ``_ALLOWED_HOSTS`` liegen (genesis.py-Muster),
sonst ``ValueError`` und es ergeht KEIN Request. Layer-Namen sind Konstanten,
niemals User-Input.

DoS-/Fehler-Schutz: ``raise_for_status()`` nach jedem Request, damit ein 5xx als
``httpx.HTTPError`` an die Fassade durchschlaegt und der STALE-ON-ERROR-Pfad
greift. Jeder Feldzugriff ist ``.get()``-defensiv (kein ``KeyError``).

Die Fetcher bauen KEINEN ``CanonicalRecord``: das Aggregieren und Normalisieren
macht der reine Mapper ``normalization/mappers/muenchen_ruhver.py``.
"""

from __future__ import annotations

import csv
import io
from urllib.parse import urlsplit

import httpx

# Hartkodierte Hosts (T-9-02 SSRF): Geoportal (WFS) + CKAN-Portal der Stadt.
_WFS_URL = "https://geoportal.muenchen.de/geoserver/mor_wfs/ows"
_CKAN_BASE = "https://opendata.muenchen.de"
_ALLOWED_HOSTS = {"opendata.muenchen.de", "geoportal.muenchen.de"}

# [VERIFIED 2026-07-29] Layer-Namen im GeoServer-Workspace mor_wfs.
_LAYER_PARKSEITEN = "mor_wfs:ruhver_parkseiten_line"
_LAYER_PRM_GEBIETE = "mor_wfs:ruhver_prm_gebiete_poly"
_LAYER_BEHINDERTENPARKPLAETZE = "mor_wfs:behindertenparkplaetze"
_LAYER_LADEN_LIEFERN = "mor_wfs:ruhver_laden_liefern_line"
_LAYER_MOBILITAETSPUNKTE = "mor_wfs:ruhver_mp_standort_point"
_LAYER_CARSHARING = "mor_wfs:ruhver_carsharing"
_LAYER_CARSHARING_STATION = "mor_wfs:ruhver_carsharing_station"
# [VERIFIED 2026-07-30] Radabstellanlagen: 3.720 bzw. 140 Datensaetze.
_LAYER_RADPARKEN = "mor_wfs:ruhver_fahrradparken_line"
_LAYER_LASTENRADPARKEN = "mor_wfs:ruhver_lastenradparken_line"

# [VERIFIED 2026-07-29] CKAN-Pakete der P+R Park & Ride GmbH Muenchen.
_PACKAGE_PR = "p-r-anlagen-muenchen"
_PACKAGE_PR_FORECAST = "p-r-anlagen-belegungsprognosen"
_PACKAGE_BR = "b-r-anlagen"

# Attribute, die aus dem Parkseiten-Layer gebraucht werden (ohne Geometrie).
_PARKSEITEN_FIELDS = "angebot,parkregel_name,parkregel_gruppe,prm_name,strasse"
# Attribute der Radabstellanlagen (die Liniengeometrie wird nicht gebraucht;
# 3.720 Datensaetze als GeoJSON waeren mehrere hundert Kilobyte).
_RADPARKEN_FIELDS = (
    "anzahl_stellplaetze,typ_generalisiert,ueberdacht,doppelstock,"
    "zusatzbeleuchtung,zeitl_begrenzung,bike_and_ride,lastenrad,standort,"
    "status_bedeutung"
)
# Attribute der PRM-Gebiete (Polygone werden nicht gebraucht).
_PRM_FIELDS = "status,massnahme,name,ueberwachung,eroeffnung"


def _wfs_params(layer: str, *, csv_fields: str | None = None) -> dict[str, str]:
    """Baut die WFS-GetFeature-Parameter fuer einen Layer.

    Ohne ``csv_fields`` wird GeoJSON in WGS84 geholt (``srsName=EPSG:4326``;
    [VERIFIED 2026-07-29]: ohne diesen Parameter antwortet der GeoServer in
    EPSG:25832 und die Koordinaten waeren Unsinn). Mit ``csv_fields`` wird CSV
    ohne Geometrie geholt (kleinere Antwort, siehe Modul-Docstring).
    """
    params = {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": layer,
    }
    if csv_fields:
        params["outputFormat"] = "csv"
        params["propertyName"] = csv_fields
    else:
        params["outputFormat"] = "application/json"
        params["srsName"] = "EPSG:4326"
    return params


async def _wfs_geojson(http: httpx.AsyncClient, layer: str) -> list[dict]:
    """Holt einen WFS-Layer als GeoJSON und liefert die ``features``-Liste."""
    resp = await http.get(_WFS_URL, params=_wfs_params(layer))
    resp.raise_for_status()
    body = resp.json()
    features = body.get("features") if isinstance(body, dict) else None
    if not isinstance(features, list):
        return []
    return [f for f in features if isinstance(f, dict)]


async def _wfs_csv(http: httpx.AsyncClient, layer: str, fields: str) -> list[dict]:
    """Holt einen WFS-Layer als CSV (ohne Geometrie) und liefert Zeilen-dicts."""
    resp = await http.get(_WFS_URL, params=_wfs_params(layer, csv_fields=fields))
    resp.raise_for_status()
    return _parse_csv(resp.content)


def _parse_csv(raw: bytes) -> list[dict]:
    """Parst CSV-Bytes defensiv zu Zeilen-dicts.

    Dekodiert als ``utf-8-sig`` ([VERIFIED 2026-07-29]: die CKAN-CSVs tragen ein
    BOM), faellt bei kaputten Bytes auf ``replace`` zurueck. Das Trennzeichen
    wird an der Kopfzeile erkannt: die P+R-Uebersicht nutzt Semikolon, die
    uebrigen Dateien Komma.
    """
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    if not text.strip():
        return []
    header = text.splitlines()[0]
    delimiter = ";" if header.count(";") > header.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    return [row for row in reader if isinstance(row, dict)]


def _point(geometry: dict | None) -> tuple[float | None, float | None]:
    """Liefert (lon, lat) als repraesentativen Punkt einer GeoJSON-Geometrie.

    Steigt defensiv bis zur ersten ``[lon, lat]``-Koordinate ab (Point,
    LineString, Polygon, MultiPolygon). Abweichende Strukturen -> (None, None)
    statt Crash (T-9-02).
    """
    node = geometry.get("coordinates") if isinstance(geometry, dict) else None
    for _ in range(5):
        if not (isinstance(node, list) and node):
            return None, None
        if isinstance(node[0], int | float):
            if len(node) >= 2 and isinstance(node[1], int | float):
                return float(node[0]), float(node[1])
            return None, None
        node = node[0]
    return None, None


def _feature_rows(features: list[dict]) -> list[dict]:
    """Reduziert GeoJSON-Features auf ``properties`` + repraesentativen Punkt."""
    rows: list[dict] = []
    for feature in features:
        props = feature.get("properties")
        props = dict(props) if isinstance(props, dict) else {}
        lon, lat = _point(feature.get("geometry"))
        props["_lat"] = lat
        props["_lon"] = lon
        rows.append(props)
    return rows


async def _ckan_csv(http: httpx.AsyncClient, package_id: str) -> list[dict]:
    """Holt die CSV-Ressource eines CKAN-Pakets ueber den 2-Step-Pfad.

    Step 1: ``package_show?id=<package_id>`` und aus ``result.resources`` die
    erste Ressource mit ``format`` CSV waehlen. Step 2: deren ``url`` gegen
    ``_ALLOWED_HOSTS`` pruefen (T-9-02 SSRF, genesis.py-Muster), dann GET und
    parsen. Kein Treffer -> leere Liste statt Crash.
    """
    pkg_resp = await http.get(
        f"{_CKAN_BASE}/api/3/action/package_show", params={"id": package_id}
    )
    pkg_resp.raise_for_status()

    body = pkg_resp.json()
    result = body.get("result") if isinstance(body, dict) else None
    resources = result.get("resources") if isinstance(result, dict) else None
    if not isinstance(resources, list):
        return []

    resource_url: str | None = None
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        fmt = str(resource.get("format") or "").lower()
        url = resource.get("url")
        if fmt == "csv" and isinstance(url, str) and url:
            resource_url = url
            break

    if not resource_url:
        return []

    if urlsplit(resource_url).hostname not in _ALLOWED_HOSTS:
        raise ValueError(
            f"entdeckte Ressourcen-URL nicht in der Allowlist: {resource_url!r}"
        )

    data_resp = await http.get(resource_url)
    data_resp.raise_for_status()
    return _parse_csv(data_resp.content)


async def fetch_muenchen_parking_onstreet(
    http: httpx.AsyncClient,
    *,
    slug: str,
    lat: float,
    lon: float,
    radius_km: float = 30.0,
) -> dict:
    """Holt den Muenchner Strassenparkraum aus vier WFS-Layern.

    ``lat``/``lon``/``radius_km`` sind vertragskonform Teil der Signatur (alle
    Stadt-Adapter teilen sie), werden hier aber nicht zur Filterung genutzt: der
    WFS liefert genau das Stadtgebiet.

    Rueckgabe-Keys (exakt das, was ``map_muenchen_parking_onstreet`` erwartet):
    ``slug``, ``segments``, ``zones``, ``accessible``, ``loading``.
    """
    segments = await _wfs_csv(http, _LAYER_PARKSEITEN, _PARKSEITEN_FIELDS)
    zones = await _wfs_csv(http, _LAYER_PRM_GEBIETE, _PRM_FIELDS)
    accessible = _feature_rows(await _wfs_geojson(http, _LAYER_BEHINDERTENPARKPLAETZE))
    loading = _feature_rows(await _wfs_geojson(http, _LAYER_LADEN_LIEFERN))

    return {
        "slug": slug,
        "segments": segments,
        "zones": zones,
        "accessible": accessible,
        "loading": loading,
    }


async def fetch_muenchen_park_and_ride(
    http: httpx.AsyncClient,
    *,
    slug: str,
    lat: float,
    lon: float,
    radius_km: float = 30.0,
) -> dict:
    """Holt P+R-Anlagen, deren Belegungsprognose und die B+R-Anlagen (CKAN).

    Drei CKAN-2-Step-Pfade. ``lat``/``lon``/``radius_km`` wie oben vertrags-
    konform, aber ohne Filterwirkung.

    Rueckgabe-Keys (exakt das, was ``map_muenchen_park_and_ride`` erwartet):
    ``slug``, ``car_rows``, ``forecast_rows``, ``bike_rows``.
    """
    car_rows = await _ckan_csv(http, _PACKAGE_PR)
    forecast_rows = await _ckan_csv(http, _PACKAGE_PR_FORECAST)
    bike_rows = await _ckan_csv(http, _PACKAGE_BR)

    return {
        "slug": slug,
        "car_rows": car_rows,
        "forecast_rows": forecast_rows,
        "bike_rows": bike_rows,
    }


async def fetch_muenchen_mobility_points(
    http: httpx.AsyncClient,
    *,
    slug: str,
    lat: float,
    lon: float,
    radius_km: float = 30.0,
) -> dict:
    """Holt Mobilitaetspunkte und die beiden Carsharing-Parkflaechen-Layer.

    ``lat``/``lon``/``radius_km`` wie oben vertragskonform, aber ohne
    Filterwirkung.

    Rueckgabe-Keys (exakt das, was ``map_muenchen_mobility_points`` erwartet):
    ``slug``, ``points``, ``carsharing_general``, ``carsharing_station``.
    """
    points = _feature_rows(await _wfs_geojson(http, _LAYER_MOBILITAETSPUNKTE))
    carsharing_general = _feature_rows(await _wfs_geojson(http, _LAYER_CARSHARING))
    carsharing_station = _feature_rows(
        await _wfs_geojson(http, _LAYER_CARSHARING_STATION)
    )

    return {
        "slug": slug,
        "points": points,
        "carsharing_general": carsharing_general,
        "carsharing_station": carsharing_station,
    }


async def fetch_muenchen_bike_parking(
    http: httpx.AsyncClient,
    *,
    slug: str,
    lat: float,
    lon: float,
    radius_km: float = 30.0,
) -> dict:
    """Holt die Rad- und Lastenradabstellanlagen aus zwei WFS-Layern.

    ``lat``/``lon``/``radius_km`` wie bei den uebrigen Fetchern vertragskonform,
    aber ohne Filterwirkung: die Layer sind stadtweit und werden vollstaendig
    geholt.

    Beide Layer teilen dasselbe Attributschema, deshalb dieselbe Feldauswahl.
    Geholt wird CSV ohne Geometrie (siehe Modul-Docstring): 3.720 Datensaetze als
    GeoJSON waeren mehrere hundert Kilobyte, ausgewertet werden ohnehin nur die
    Attribute.

    Rueckgabe-Keys (exakt das, was ``map_muenchen_bike_parking`` erwartet):
    ``slug``, ``bike``, ``cargo``.
    """
    bike = await _wfs_csv(http, _LAYER_RADPARKEN, _RADPARKEN_FIELDS)
    cargo = await _wfs_csv(http, _LAYER_LASTENRADPARKEN, _RADPARKEN_FIELDS)

    return {"slug": slug, "bike": bike, "cargo": cargo}
