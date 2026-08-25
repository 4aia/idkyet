"""Reiner DB-BahnPark-Parken-Mapper ``map_db_bahnpark`` (Phase 25, PARK-05, Tier A).

Übersetzt das rohe Adapter-dict aus ``adapters/db_bahnpark`` deterministisch in
einen ``CanonicalRecord``. Schablone ist ``mappers/mobilithek_parken.
map_dortmund_parking``: rein (kein HTTP, kein Parse, keine Systemuhr),
``retrieved_at`` keyword-only injiziert.

Die ``facilities`` (je Bahnhof-Parkeinrichtung facility_id + free/total/occupancy,
``lot_type="station"``) wandern in den ``ParkingPayload``. Reine Live-Daten ->
``geo=None``; ``observed_at`` aus dem jüngsten Belegungs-Zeitstempel (``as_of``)
falls vorhanden, sonst ``None`` (ehrlich, keine Systemuhr).

Lizenz: Datenlizenz Deutschland Namensnennung 2.0 (DL-DE/BY 2.0) = Tier A,
Attribution "DB BahnPark GmbH" (verbatim aus 25-01 / source_specs).
"""

from __future__ import annotations

from datetime import datetime

from infranode.normalization import (
    Attribution,
    CanonicalRecord,
    LicenseId,
    LicenseTier,
    ParkingPayload,
    SourceId,
)

_DL_DE_BY_URL = "https://www.govdata.de/dl-de/by-2-0"
# Wörtlicher Quellenvermerk laut Servicebedingungen des DB API Marketplace
# (verifiziert 2026-07-20; dl-de/by-2-0 verlangt genau diese Namensnennung).
_DB_BAHNPARK_ATTRIBUTION = (
    "Parking Information Daten der DB BahnPark, API über den DB API Marketplace "
    "(https://developers.deutschebahn.com/db-api-marketplace/apis/product/"
    "parking-information-db-bahnpark)"
)


def _parse_as_of(raw: dict) -> datetime | None:
    """Liest ``as_of`` (jüngster Belegungs-Zeitstempel) als aware ``datetime``.

    Rein (keine Systemuhr). Ein nicht-parsebarer/fehlender Wert -> ``None``
    (ehrlich, kein Fehler).
    """
    text = raw.get("as_of")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except (ValueError, TypeError):
        return None


def map_db_bahnpark(
    raw: dict,
    *,
    retrieved_at: datetime,
    ags: str | None = None,
    wikidata_qid: str | None = None,
) -> CanonicalRecord:
    """Bildet die DB-BahnPark-Belegung (parking) auf einen ``CanonicalRecord`` ab.

    Die ``facilities`` (Bahnhof-Parken, ``lot_type="station"``) wandern in den
    ``ParkingPayload``. ``observed_at`` aus dem jüngsten Belegungs-Zeitstempel
    (``as_of``) falls vorhanden. ``retrieved_at`` injiziert (keine Systemuhr im
    Mapper). Tier A, DL-DE/BY 2.0, Attribution "DB BahnPark GmbH".
    """
    return CanonicalRecord(
        city_slug=raw["slug"],
        geo=None,
        observed_at=_parse_as_of(raw),
        retrieved_at=retrieved_at,
        source=SourceId.DB_BAHNPARK,
        license_id=LicenseId.DL_DE_BY_2_0,
        license_tier=LicenseTier.A,
        ags=ags,
        wikidata_qid=wikidata_qid,
        attribution=Attribution(
            text=_DB_BAHNPARK_ATTRIBUTION,
            license_url=_DL_DE_BY_URL,
        ),
        payload=ParkingPayload(
            facilities=raw.get("facilities", []),
        ),
    )
