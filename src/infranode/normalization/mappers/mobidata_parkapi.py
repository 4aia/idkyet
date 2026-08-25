"""Reiner MobiData-BW-ParkAPI-Mapper map_mobidata_parking (PARK-01/02/03, Tier A).

Übersetzt das rohe Adapter-dict (``slug``/``facilities``/``as_of``) deterministisch in
einen ``CanonicalRecord`` mit ``ParkingPayload``. Rein: kein HTTP, keine Systemuhr
(``retrieved_at`` keyword-only injiziert). Vorlage ist
``mappers/parkendd.map_parkendd``.

LIZENZ (PARK-03): Die MobiData-BW-ParkAPI aggregiert heterogen lizenzierte
Stadt-/Betreiber-Quellen; ``/v3/sources`` deklariert die Lizenz nur bei wenigen
Quellen (viele NULL). Die Lizenz wird daher PRO STADT am echten Ursprung verifiziert
(``_MOBIDATA_LICENSE``) und mit korrektem Tier getragen. Es werden NUR Städte mit
offener Standardlizenz ausgeliefert (dl-de/by, CC-BY, CC0). NULL-Quellen ohne offenen
Nachweis (z.B. kommerzielle Betreiberportale ohne Open-Data-Deklaration) werden NICHT
aufgenommen und bleiben not_covered (T-25-06).

karlsruhe wird bewusst NICHT ausgeliefert: der Live-Verify von ``source_uid=karlsruhe``
(2026-07-19) bestätigte die Anomalie aus der Recherche (T-25-07): die Quelle
(source_id 12) liefert fremdstädtische Sites (Bädergarage/Vincentigarage in
Baden-Baden, official_region_code 082110000000) gemischt mit Karlsruher Sites und
durchgängig ``has_realtime_data = false`` mit eingefrorenem
``static_data_updated_at = 2023-12-31``. Damit ist über MobiData keine Karlsruher
Realtime-Belegung beziehbar; karlsruhe bleibt bis zur Klärung ungelöst (Regress-Risiko
für das 25-08-Paritäts-Gate, da karlsruhe heute noch LIVE via ParkenDD ist).
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

_MOBIDATA_URL = "https://api.mobidata-bw.de/park-api"

# Kanonische Lizenz-Deed-URL je LicenseId (Attribution.license_url). Für nicht
# gelistete (UNKNOWN) Lizenzen bleibt die ParkAPI-Quellseite die Quellangabe.
_LICENSE_DEED: dict[LicenseId, str] = {
    LicenseId.DL_DE_BY_2_0: "https://www.govdata.de/dl-de/by-2-0",
    LicenseId.DL_DE_ZERO_2_0: "https://www.govdata.de/dl-de/zero-2-0",
    LicenseId.CC0: "https://creativecommons.org/publicdomain/zero/1.0/",
    LicenseId.CC_BY_4_0: "https://creativecommons.org/licenses/by/4.0/",
}

# Per-Stadt-Lizenz der MobiData-URSPRUNGSQUELLE (am Ursprung verifiziert, PARK-03):
# slug -> (LicenseId, LicenseTier, attribution_text). Attribution wortgenau identisch
# zu DATA-LICENSES.md (T-11-SRC-DRIFT). Es sind exakt die BW-ParkenDD-Städte mit
# offener Standardlizenz UND beziehbarer Realtime-Belegung: freiburg (dl-de/by),
# heidelberg (CC-BY), heilbronn (dl-de/by, Namensnennung "Stadtwerke Heilbronn"
# wortgenau, NICHT "Stadt Heilbronn"), ulm (CC0). karlsruhe (Anomalie, s. Modul-
# Docstring) und die kommerzielle NULL-Betreiberquelle ohne offenen Nachweis sind
# bewusst NICHT gelistet -> not_covered.
_MOBIDATA_LICENSE: dict[str, tuple[LicenseId, LicenseTier, str]] = {
    "freiburg-im-breisgau": (
        LicenseId.DL_DE_BY_2_0,
        LicenseTier.A,
        "Stadt Freiburg",
    ),
    "heidelberg": (
        LicenseId.CC_BY_4_0,
        LicenseTier.A,
        "Stadt Heidelberg, Amt für Mobilität",
    ),
    "heilbronn": (LicenseId.DL_DE_BY_2_0, LicenseTier.A, "Stadtwerke Heilbronn"),
    "ulm": (LicenseId.CC0, LicenseTier.A, "Stadt Ulm"),
}

# Fail-safe für einen nicht gelisteten Slug (sollte nie ausgeliefert werden, da die
# Connector-Registry deckungsgleich mit den Schlüsseln dieser Map ist): ehrlich
# UNKNOWN/Tier C.
_DEFAULT_LICENSE: tuple[LicenseId, LicenseTier, str] = (
    LicenseId.UNKNOWN,
    LicenseTier.C,
    "MobiData BW / ParkAPI",
)


def _parse_as_of(value: object) -> datetime | None:
    """Parst den ParkAPI-``realtime_data_updated_at``-String defensiv (sonst None)."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def map_mobidata_parking(
    raw: dict,
    *,
    retrieved_at: datetime,
    ags: str | None = None,
    wikidata_qid: str | None = None,
) -> CanonicalRecord:
    """Bildet rohe MobiData-ParkAPI-Parkdaten auf einen ``CanonicalRecord`` ab.

    Die ``facilities`` (Sites mit frei/gesamt/occupancy/Zustand) wandern unverändert in
    den ``ParkingPayload``. ``observed_at`` kommt aus dem Datenstand (``as_of``),
    ``geo=None`` (Koordinaten je Facility im Payload). ``license_id``/``license_tier``/
    Attribution kommen PRO STADT aus ``_MOBIDATA_LICENSE`` (am Ursprung verifiziert);
    nicht gelistete Slugs fallen ehrlich auf UNKNOWN/Tier C (Fail-safe).
    """
    slug = raw["slug"]
    license_id, license_tier, attribution_text = _MOBIDATA_LICENSE.get(
        slug, _DEFAULT_LICENSE
    )
    license_url = _LICENSE_DEED.get(license_id, _MOBIDATA_URL)
    return CanonicalRecord(
        city_slug=slug,
        geo=None,
        observed_at=_parse_as_of(raw.get("as_of")),
        retrieved_at=retrieved_at,
        source=SourceId.MOBIDATA_PARKAPI,
        license_id=license_id,
        license_tier=license_tier,
        ags=ags,
        wikidata_qid=wikidata_qid,
        attribution=Attribution(
            text=attribution_text,
            license_url=license_url,
        ),
        payload=ParkingPayload(
            facilities=raw.get("facilities", []),
        ),
    )
