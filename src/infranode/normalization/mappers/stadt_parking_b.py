"""Reine Stadt-OpenData-Parkmapper (PARK-06) - Teil B: Kaiserslautern + Karlsruhe.

Getrennt von ``mappers/stadt_parking.py`` (Teil A: Muenster/Aachen/Oldenburg,
Plan 25-03), damit die parallel laufenden Wave-1-Slices keine gemeinsame
Mapper-Datei schreiben.

Uebersetzt das rohe Adapter-dict (``slug``/``facilities``/``as_of``)
deterministisch in einen ``CanonicalRecord`` mit ``ParkingPayload``. Rein: kein
HTTP, keine Systemuhr (``retrieved_at`` keyword-only injiziert), ``geo=None``.
Vorlage ist ``mappers/stadt_parking._build``.

LIZENZ (PARK-06, T-25-10), wortgenau identisch zu ``DATA-LICENSES.md`` und
``registry/source_specs`` (T-11-SRC-DRIFT):
- Kaiserslautern: CC0, "Stadtverwaltung Kaiserslautern"
  (live verifiziert 2026-07-19: Datensatz ``parkhausbelegung`` ``cc-zero``).
- Karlsruhe (regress-kritisch): CC-BY 4.0, "Stadt Karlsruhe", Tier A (verifiziert
  2026-07-19: Transparenzportal-Datensatz parkhaeuser, WFS-JSON). Direkter
  ParkenDD-Ersatz (gleiche Datenbasis, offiziell lizenziert).

Dresden ist hier bewusst NICHT enthalten: der keylose Realtime-Ursprung konnte in
Plan 25-04 nicht positiv verifiziert werden (Owner-Checkpoint-Entscheidung
``accept-nodata``); siehe 25-04-SUMMARY (Regress-Risiko fuer das 25-08-Gate).
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

# Kanonische Lizenz-Deed-URL je LicenseId (Attribution.license_url).
_LICENSE_DEED: dict[LicenseId, str] = {
    LicenseId.DL_DE_BY_2_0: "https://www.govdata.de/dl-de/by-2-0",
    LicenseId.DL_DE_ZERO_2_0: "https://www.govdata.de/dl-de/zero-2-0",
    LicenseId.CC0: "https://creativecommons.org/publicdomain/zero/1.0/",
    LicenseId.CC_BY_4_0: "https://creativecommons.org/licenses/by/4.0/",
}

# Defensiver Fallback für nicht in _LICENSE_DEED gelistete license_ids (aktuell nutzt
# keine Quelle dieser Datei UNKNOWN; kaiserslautern=CC0, karlsruhe=CC-BY 4.0).
_UNKNOWN_URL = "https://www.govdata.de/dl-de/zero-2-0"


def _parse_as_of(value: object) -> datetime | None:
    """Parst den Stadt-OpenData-``as_of``-String defensiv zu datetime (sonst None)."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _build(
    raw: dict,
    *,
    source: SourceId,
    license_id: LicenseId,
    license_tier: LicenseTier,
    attribution_text: str,
    retrieved_at: datetime,
    ags: str | None,
    wikidata_qid: str | None,
) -> CanonicalRecord:
    """Gemeinsamer reiner Aufbau des ``CanonicalRecord`` (keine Systemuhr, geo=None)."""
    return CanonicalRecord(
        city_slug=raw["slug"],
        geo=None,
        observed_at=_parse_as_of(raw.get("as_of")),
        retrieved_at=retrieved_at,
        source=source,
        license_id=license_id,
        license_tier=license_tier,
        ags=ags,
        wikidata_qid=wikidata_qid,
        attribution=Attribution(
            text=attribution_text,
            license_url=_LICENSE_DEED.get(license_id, _UNKNOWN_URL),
        ),
        payload=ParkingPayload(
            facilities=raw.get("facilities", []),
        ),
    )


def map_kaiserslautern_parking(
    raw: dict,
    *,
    retrieved_at: datetime,
    ags: str | None = None,
    wikidata_qid: str | None = None,
) -> CanonicalRecord:
    """Bildet rohe Kaiserslautern-Parkdaten auf einen ``CanonicalRecord`` (Tier A) ab.

    Regress-kritisch (heute LIVE via ParkenDD): CC0, Datenherausgeber
    "Stadtverwaltung Kaiserslautern".
    """
    return _build(
        raw,
        source=SourceId.KAISERSLAUTERN_PARKING,
        license_id=LicenseId.CC0,
        license_tier=LicenseTier.A,
        attribution_text="Stadtverwaltung Kaiserslautern",
        retrieved_at=retrieved_at,
        ags=ags,
        wikidata_qid=wikidata_qid,
    )


def map_karlsruhe_parking(
    raw: dict,
    *,
    retrieved_at: datetime,
    ags: str | None = None,
    wikidata_qid: str | None = None,
) -> CanonicalRecord:
    """Bildet rohe Karlsruhe-Parkdaten auf einen ``CanonicalRecord`` (Tier A) ab.

    Regress-kritisch (heute LIVE via ParkenDD). Direktbezug aus dem offiziellen
    CC-BY-4.0-Parkhaus-Datensatz der Stadt Karlsruhe (Transparenzportal
    ``transparenz.karlsruhe.de/dataset/parkhaeuser``, WFS-JSON). LIZENZ verifiziert
    2026-07-19: Creative Commons Namensnennung 4.0 International (CC-BY 4.0),
    Herausgeber "Stadt Karlsruhe" -> Tier A (public). Ersetzt die frühere
    konservative UNKNOWN/Tier-C-Einstufung des lizenzlosen HTML-Endpunkts.
    """
    return _build(
        raw,
        source=SourceId.KARLSRUHE_PARKING,
        license_id=LicenseId.CC_BY_4_0,
        license_tier=LicenseTier.A,
        attribution_text="Stadt Karlsruhe",
        retrieved_at=retrieved_at,
        ags=ags,
        wikidata_qid=wikidata_qid,
    )
