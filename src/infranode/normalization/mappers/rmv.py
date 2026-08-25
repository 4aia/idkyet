"""Mapper: RMV-HAPI Live-Abfahrten -> CanonicalRecord (Quick-260707-mmi, Tier C).

Bildet das raw-dict des ``adapters.rmv.fetch_rmv_departures`` (Station + schlanke
Abfahrts-dicts inkl. Verspätung) auf den kanonischen Envelope ab. Wiederverwendung
von ``TransitDeparturePayload`` (Phase 19), da die Form identisch ist: ``stop_id``
+ ``departures`` (Liste schlanker dicts).

KRITISCH: RMV-HAPI ist Tier C (live-only). Die Lizenz ist nicht offen
(registrierungspflichtiger accessId) -> ``license_id = UNKNOWN``, reine Live-
Anzeige, KEIN Archiv. Die Attribution nennt den RMV als Quelle (Pflicht).
``retrieved_at`` wird injiziert (keine Systemuhr im Mapper).
"""

from __future__ import annotations

from datetime import datetime

from infranode.normalization import (
    Attribution,
    CanonicalRecord,
    LicenseId,
    LicenseTier,
    SourceId,
)
from infranode.normalization.payloads import TransitDeparturePayload

_RMV_ATTRIBUTION = "Rhein-Main-Verkehrsverbund GmbH (RMV)"


def map_rmv_departures(
    raw: dict,
    *,
    retrieved_at: datetime,
    ags: str | None = None,
    wikidata_qid: str | None = None,
    city_slug: str = "frankfurt-am-main",
) -> CanonicalRecord:
    """Bildet RMV-HAPI-Live-Abfahrten auf einen ``CanonicalRecord`` ab (Tier C).

    Die normalisierten ``departures`` (je Abfahrt: line/direction/in_minutes/
    delay_s/alerts) wandern in den ``TransitDeparturePayload``. Tier C live-only,
    Lizenz UNKNOWN (RMV-HAPI nicht offen), KEIN Archiv.
    """
    return CanonicalRecord(
        city_slug=city_slug,
        geo=None,
        observed_at=None,
        retrieved_at=retrieved_at,
        source=SourceId.RMV,
        license_id=LicenseId.UNKNOWN,
        license_tier=LicenseTier.C,
        ags=ags,
        wikidata_qid=wikidata_qid,
        attribution=Attribution(text=_RMV_ATTRIBUTION, license_url=None),
        payload=TransitDeparturePayload(
            stop_id=raw.get("stop_id"),
            departures=raw.get("departures", []),
        ),
    )
