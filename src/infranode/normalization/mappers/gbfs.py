"""Reiner GBFS-Sharing-Mapper ``map_sharing`` (DATA-33, Tier A).

Übersetzt das aggregierte GBFS-raw-dict (aus ``adapters.gbfs.fetch_sharing``)
deterministisch in einen ``CanonicalRecord`` mit ``SharingPayload``. Rein: kein
HTTP, kein Logging, kein ``datetime.now()`` (``retrieved_at`` wird injiziert).

Die Stadt-Kennzahlen (vehicles_available etc.) sind aus den Einzelfahrzeugen/
Stationen VERRECHNET (Summen, BBox-Filter), daher ``modified=True``.

Lizenz: je Anbieter wird die Lizenz im Adapter fail-closed gegen die Tier-A-
Allowlist geprüft und im Payload je Anbieter ausgewiesen. Die record-weite Lizenz
und Attribution werden aus den tatsächlichen Providern ABGELEITET (nicht mehr
pauschal CC0): reines Nextbike -> CC0, Attribution "nextbike GmbH / GBFS (CC0)";
Frankfurt am Main -> DB Call a Bike über MobiData BW, DL-DE/BY-2.0, Attribution
"Deutsche Bahn Connect GmbH / MobiData BW, DL-DE/BY-2.0". Alle akzeptierten Systeme
sind fail-closed Tier A. (Die Attributionen müssen verbatim in DATA-LICENSES.md
stehen.)
"""

from __future__ import annotations

from datetime import datetime

from infranode.normalization import (
    Attribution,
    CanonicalRecord,
    GeoPoint,
    LicenseId,
    LicenseTier,
    SharingPayload,
    SourceId,
)

_CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"

# Kanonischer Lizenz-Tag -> Lizenz-URL. Die govdata-URL ist projektweit die
# Konvention (vgl. mappers/autobahn.py ``_DL_DE_BY_URL``). Unbekannter Tag ->
# CC0-URL-Fallback (greift praktisch nicht, da die Tags aus der Tier-A-Allowlist
# des Adapters stammen).
_LICENSE_URLS: dict[str, str] = {
    "cc0": _CC0_URL,
    "dl_de_by_2_0": "https://www.govdata.de/dl-de/by-2-0",
    "cc_by_4_0": "https://creativecommons.org/licenses/by/4.0/",
}

# Fallback, wenn ein raw-dict unerwartet KEINE Provider trägt (die Route fängt den
# no_data-Fall bereits vor dem Mapper ab; der Mapper wird nur mit providers != []
# aufgerufen). Dann bleibt die Nextbike-Primärquelle CC0.
_FALLBACK_ATTRIBUTION = "nextbike GmbH / GBFS (CC0)"
_FALLBACK_TAG = "cc0"


def map_sharing(
    raw: dict,
    *,
    retrieved_at: datetime,
    ags: str | None = None,
    wikidata_qid: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> CanonicalRecord:
    """Bildet den aggregierten GBFS-Sharing-Snapshot auf einen ``CanonicalRecord`` ab.

    ``lat``/``lon`` stammen aus dem Register (die Kennzahl aggregiert Fahrzeuge/
    Stationen im Umkreis dieser Koordinate). ``modified=True``, weil die Stadt-
    Aggregate aus den Einzelfahrzeugen berechnet sind. ``observed_at`` kommt aus
    dem jüngsten GBFS-``last_updated`` der Feeds (H9, UTC-ISO im raw-dict); fehlt
    er, bleibt er ``None`` (der Zeitbezug steckt dann in ``retrieved_at``).
    """
    geo = GeoPoint(lat=lat, lon=lon) if lat is not None and lon is not None else None
    observed_raw = raw.get("observed_at")
    observed_at = None
    if isinstance(observed_raw, str) and observed_raw:
        try:
            observed_at = datetime.fromisoformat(observed_raw)
        except ValueError:
            observed_at = None

    # Record-weite Lizenz + Attribution aus den tatsächlichen Providern ableiten
    # (Reihenfolge erhalten, dedupliziert). Tragen alle Provider denselben Tag, ist
    # das der record_tag; bei (aktuell nicht auftretender) Mischung führt die
    # Provider-Ebene je Anbieter die exakte license_id, record_tag nimmt den ersten
    # Provider als primären. Leere Provider -> Nextbike/CC0-Fallback.
    providers = raw.get("providers", [])
    tags = list(
        dict.fromkeys(p.get("license_id") for p in providers if p.get("license_id"))
    )
    attributions = list(
        dict.fromkeys(p.get("attribution") for p in providers if p.get("attribution"))
    )
    record_tag = tags[0] if tags else _FALLBACK_TAG
    attribution_text = (
        "; ".join(attributions) if attributions else _FALLBACK_ATTRIBUTION
    )
    record_license = LicenseId(record_tag)
    license_url = _LICENSE_URLS.get(record_tag, _CC0_URL)

    return CanonicalRecord(
        city_slug=raw["slug"],
        geo=geo,
        observed_at=observed_at,
        retrieved_at=retrieved_at,
        source=SourceId.GBFS,
        license_id=record_license,
        license_tier=LicenseTier.A,
        ags=ags,
        wikidata_qid=wikidata_qid,
        attribution=Attribution(
            text=attribution_text,
            license_url=license_url,
            modified=True,
        ),
        payload=SharingPayload(
            radius_km=raw.get("radius_km"),
            vehicles_available=raw.get("vehicles_available", 0),
            free_floating_available=raw.get("free_floating_available", 0),
            docked_available=raw.get("docked_available", 0),
            station_count=raw.get("station_count", 0),
            providers=raw.get("providers", []),
        ),
    )
