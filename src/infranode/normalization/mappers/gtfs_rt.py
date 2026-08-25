"""Reiner GTFS-RT-Mapper (Phase 19, Tier B / CC-BY-SA).

Übersetzt die rohen Trip-Update-/Aggregat-dicts (aus ``adapters/gtfs_rt.py`` bzw.
den Live-Routen) deterministisch in einen ``CanonicalRecord``:
- ``map_transit_trip``: ein einzelnes Trip-Update inkl. geschätzter Position
  -> ``TransitTripPayload`` (TRANSIT-RT-04).
- ``map_transit_departures``: Abfahrten je Halt -> ``TransitDeparturePayload``
  (TRANSIT-RT-03).
- ``map_transit_route_status``: aggregierte Verspätungslage einer Linie
  -> ``TransitRouteStatusPayload`` (TRANSIT-RT-05).

Schablone ist ``mappers/mobilithek_koeln.py`` (exakt: rein, kein HTTP/Parse, keine
Systemuhr, ``retrieved_at`` keyword-only injiziert), ABER mit dem entscheidenden
Unterschied der Lizenzklasse: gtfs.de/DELFI-Realtime steht unter CC-BY-SA 4.0 =
``license_tier=B`` (copyleft, getrennt vom Tier-A-Archiv halten, CONTEXT LOCKED),
NICHT Tier A wie der Köln-Mapper (DL-DE/Zero). Attribution "gtfs.de" (Primärquelle)
bzw. "DELFI e.V." (Mobilithek), Lizenz-URL CC-BY-SA.

``geo=None`` (die geschätzte Position liegt im Payload, nicht im Envelope-Geo);
``observed_at`` aus dem RT-FeedHeader-Timestamp (``timestamp``) falls vorhanden,
sonst ``None`` (ehrlich, keine Systemuhr). KEIN ``append_record`` (Tier B,
T-19-ARCHIVE): reine Live-Daten werden NIE archiviert.
"""

from __future__ import annotations

from datetime import UTC, datetime

from infranode.normalization import (
    Attribution,
    CanonicalRecord,
    LicenseId,
    LicenseTier,
    SourceId,
)
from infranode.normalization.payloads import (
    TransitDeparturePayload,
    TransitRouteStatusPayload,
    TransitTripPayload,
)

# Attribution-Texte je Quelle (CONTEXT LOCKED): gtfs.de = Primärquelle,
# DELFI e.V. = Mobilithek-Realtime. Beide CC-BY-SA 4.0 (Tier B copyleft).
_GTFS_DE_ATTRIBUTION = "gtfs.de"
_DELFI_ATTRIBUTION = "DELFI e.V."
_CC_BY_SA_URL = "https://creativecommons.org/licenses/by-sa/4.0/"

# quick-260707-kzd: VBB-Berlin steht unter CC-BY 4.0 (permissiv, Tier A), NICHT
# CC-BY-SA wie gtfs.de/DELFI. Eigener Attribution-Text + eigene Lizenz-URL, damit
# die Provenance je Quelle ehrlich bleibt (keine Lizenzvermischung).
_VBB_ATTRIBUTION = "VBB"
_CC_BY_URL = "https://creativecommons.org/licenses/by/4.0/"


def attribution_for_source(used_source: str | None) -> str:
    """Waehlt den Attribution-Text aus der RT-Provenance (VBB vs DELFI vs gtfs.de).

    ``"vbb"`` -> "VBB" (CC-BY 4.0, Tier A), ``"mobilithek_delfi"`` -> "DELFI e.V.",
    sonst (gtfs.de-Backup/Default) "gtfs.de". Fuer DELFI/gtfs.de bleibt es
    CC-BY-SA 4.0 Tier B (CONTEXT LOCKED); die Lizenzwahl selbst trifft
    ``map_transit_departures`` ueber ``used_source``.
    """
    if used_source == "vbb":
        return _VBB_ATTRIBUTION
    if used_source == "mobilithek_delfi":
        return _DELFI_ATTRIBUTION
    return _GTFS_DE_ATTRIBUTION


def _observed_at(raw: dict) -> datetime | None:
    """Liest den RT-Feed-Timestamp (Unix-Epoch) als aware ``datetime`` oder None.

    Rein (keine Systemuhr): ein fehlender/nicht-interpretierbarer Wert -> ``None``
    (ehrlich, kein Fehler).
    """
    ts = raw.get("timestamp")
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=UTC)
    except (ValueError, TypeError, OSError):
        return None


def _attribution(
    *, source_attribution: str, license_url: str = _CC_BY_SA_URL
) -> Attribution:
    """Baut die Attribution mit der passenden Lizenz-URL.

    Default ``_CC_BY_SA_URL`` (Tier B, gtfs.de/DELFI) -> bestehende Aufrufer/Tests
    bleiben unveraendert; VBB reicht ``license_url=_CC_BY_URL`` (Tier A, CC-BY 4.0)
    durch.
    """
    return Attribution(text=source_attribution, license_url=license_url)


def map_transit_trip(
    raw: dict,
    *,
    retrieved_at: datetime,
    city_slug: str,
    ags: str | None = None,
    wikidata_qid: str | None = None,
    source_attribution: str = _GTFS_DE_ATTRIBUTION,
) -> CanonicalRecord:
    """Bildet ein einzelnes Trip-Update auf einen ``CanonicalRecord`` ab (Tier B).

    Reicht ``trip_id``/``route_id``/``delay_s`` durch und übernimmt die bereits
    interpolierte ``estimated_position`` unverändert in den Payload. ``unresolved``
    True heisst: die ``trip_id`` war nicht gegen das statische GTFS auflösbar
    (ehrlich statt 500, RESEARCH Pitfall 4). ``retrieved_at`` injiziert (keine
    Systemuhr im Mapper).
    """
    return CanonicalRecord(
        city_slug=city_slug,
        geo=None,
        observed_at=_observed_at(raw),
        retrieved_at=retrieved_at,
        source=SourceId.GTFS_RT,
        license_id=LicenseId.CC_BY_SA_4_0,
        license_tier=LicenseTier.B,
        ags=ags,
        wikidata_qid=wikidata_qid,
        attribution=_attribution(source_attribution=source_attribution),
        payload=TransitTripPayload(
            trip_id=raw["trip_id"],
            route_id=raw.get("route_id"),
            delay_s=raw.get("delay"),
            estimated_position=raw.get("estimated_position"),
            stop_time_updates=raw.get("stop_time_updates", []),
            unresolved=raw.get("unresolved", False),
        ),
    )


def map_transit_departures(
    raw: dict,
    *,
    retrieved_at: datetime,
    city_slug: str,
    ags: str | None = None,
    wikidata_qid: str | None = None,
    source_attribution: str = _GTFS_DE_ATTRIBUTION,
    used_source: str | None = None,
) -> CanonicalRecord:
    """Bildet Abfahrten je Halt auf einen ``CanonicalRecord`` ab.

    Die ``departures`` (je Abfahrt ein schlankes dict) wandern in den
    ``TransitDeparturePayload``. ``retrieved_at`` injiziert (keine Systemuhr).

    quick-260707-kzd: die Lizenzklasse folgt ``used_source``. Bei ``"vbb"`` ->
    CC-BY 4.0 / Tier A (permissiv, VBB); sonst (Default ``None`` und alle
    Bestandswerte) unveraendert CC-BY-SA 4.0 / Tier B (gtfs.de/DELFI). Der
    Default-Pfad laesst die bestehenden Tests unveraendert bestehen.
    """
    if used_source == "vbb":
        license_id = LicenseId.CC_BY_4_0
        license_tier = LicenseTier.A
        attribution = _attribution(
            source_attribution=source_attribution, license_url=_CC_BY_URL
        )
    else:
        license_id = LicenseId.CC_BY_SA_4_0
        license_tier = LicenseTier.B
        attribution = _attribution(source_attribution=source_attribution)
    return CanonicalRecord(
        city_slug=city_slug,
        geo=None,
        observed_at=_observed_at(raw),
        retrieved_at=retrieved_at,
        source=SourceId.GTFS_RT,
        license_id=license_id,
        license_tier=license_tier,
        ags=ags,
        wikidata_qid=wikidata_qid,
        attribution=attribution,
        payload=TransitDeparturePayload(
            stop_id=raw.get("stop_id"),
            departures=raw.get("departures", []),
        ),
    )


def map_transit_route_status(
    raw: dict,
    *,
    retrieved_at: datetime,
    city_slug: str,
    ags: str | None = None,
    wikidata_qid: str | None = None,
    source_attribution: str = _GTFS_DE_ATTRIBUTION,
) -> CanonicalRecord:
    """Bildet die aggregierte Verspätungslage einer Linie ab (Tier B).

    ``active_trips``/``avg_delay_s``/``max_delay_s``/``trips`` werden vom Aufrufer
    (Live-Route) aggregiert und hier in den ``TransitRouteStatusPayload``
    durchgereicht. ``retrieved_at`` injiziert (keine Systemuhr).
    """
    return CanonicalRecord(
        city_slug=city_slug,
        geo=None,
        observed_at=_observed_at(raw),
        retrieved_at=retrieved_at,
        source=SourceId.GTFS_RT,
        license_id=LicenseId.CC_BY_SA_4_0,
        license_tier=LicenseTier.B,
        ags=ags,
        wikidata_qid=wikidata_qid,
        attribution=_attribution(source_attribution=source_attribution),
        payload=TransitRouteStatusPayload(
            route_id=raw.get("route_id"),
            active_trips=raw.get("active_trips", 0),
            avg_delay_s=raw.get("avg_delay_s"),
            max_delay_s=raw.get("max_delay_s"),
            trips=raw.get("trips", []),
        ),
    )
