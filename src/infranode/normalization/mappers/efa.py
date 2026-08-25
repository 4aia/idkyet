"""Generischer Mapper: Mentz-EFA Live-Abfahrten -> CanonicalRecord (Tier C).

Bildet das raw-dict des ``adapters.efa.fetch_efa_departures`` (Station + schlanke
Abfahrts-dicts inkl. Verspaetung) auf den kanonischen Envelope ab. Wiederverwendung
von ``TransitDeparturePayload`` (Phase 19, wie HVV-Geofox/RMV/VGN), da die Form
identisch ist: ``stop_id`` + ``departures``.

GENERISCH ueber ``source`` + ``attribution`` parametrisiert (Reuse-Ziel): die
ERSTE Instanz ist der VRR (SourceId.VRR, "Verkehrsverbund Rhein-Ruhr (VRR)"), der
VVS Stuttgart nutzt denselben Mapper spaeter mit SourceId.VVS + eigener
Attribution OHNE Aenderung.

KRITISCH: Mentz-EFA ist Tier C (live-only). Die Lizenz ist nicht klar offen ->
``license_id = UNKNOWN``, reine Live-Anzeige, KEIN Archiv (analog HVV-Geofox/RMV).
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


def map_efa_departures(
    raw: dict,
    *,
    retrieved_at: datetime,
    source: SourceId,
    attribution: str,
    ags: str | None = None,
    wikidata_qid: str | None = None,
    city_slug: str,
) -> CanonicalRecord:
    """Bildet Mentz-EFA-Live-Abfahrten auf einen ``CanonicalRecord`` ab (Tier C).

    ``source`` (SourceId) und ``attribution`` (Text) sind parametrisiert, damit
    jeder EFA-Verbund denselben Mapper nutzt. Die normalisierten ``departures``
    (je Abfahrt line/direction/in_minutes/delay_s/alerts) wandern in den
    ``TransitDeparturePayload``. Tier C live-only, Lizenz UNKNOWN, KEIN Archiv.
    """
    return CanonicalRecord(
        city_slug=city_slug,
        geo=None,
        observed_at=None,
        retrieved_at=retrieved_at,
        source=source,
        license_id=LicenseId.UNKNOWN,
        license_tier=LicenseTier.C,
        ags=ags,
        wikidata_qid=wikidata_qid,
        attribution=Attribution(text=attribution, license_url=None),
        payload=TransitDeparturePayload(
            stop_id=raw.get("stop_id"),
            departures=raw.get("departures", []),
        ),
    )
