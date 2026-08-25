"""Redis-Store für kompakte, indizierte GTFS-RT-Updates (Phase 19, Plan 04).

Schreibt NUR die kompakten, vom Adapter geparsten Trip-Update-dicts in Redis,
NIE den rohen 68-MB-Feed (Anti-Pattern, RESEARCH Pitfall 1: ein roher Feed-Body
in Redis sprengt den Speicher der 4-GB-Box und macht jeden Lese-Pfad teuer). Der
Hintergrund-Poller (``transit/poller.py``) parst den Feed EINMAL je Kadenz und
ruft ``store_updates_indexed``; der Request-Pfad (``api/v1/live.py``) liest dann
NUR über die Lese-Helfer (kein Parse im Request, T-19-REQPARSE).

Key-Layout (versioniert mit ``v1``-Präfix, analog ``infra/cache.build_cache_key``,
T-19-CACHEPOISON: trip_id/stop_id/route_id sind vom Aufrufer validiert, nie ein
roher User-String):
- ``transit_rt:v1:{trip_id}``        -> orjson-serialisiertes Update-dict (SET ex)
- ``transit_rt:idx:stop:{stop_id}``  -> Set der trip_ids, die diesen Halt bedienen
- ``transit_rt:idx:route:{route_id}``-> Set der trip_ids dieser Linie

Alle Keys tragen eine TTL: ein neuer Poller-Lauf überschreibt frische Daten, und
fällt der Poller aus, verfallen veraltete Updates automatisch (nur aktuellster
Stand, CONTEXT LOCKED). KEIN Archiv-Write (Tier B, T-19-ARCHIVE): reine
Live-Daten werden NIE in das Tier-A-Archiv geschrieben.
"""

from __future__ import annotations

import orjson

# Gemeinsamer Basis-Präfix aller RT-Keys. Der optionale ``namespace`` (leer = der
# bestehende Keyspace, "vbb:" = der isolierte VBB-Keyspace) wird direkt dahinter
# eingesetzt, sodass Default namespace="" EXAKT die Bestands-Keys erzeugt
# (transit_rt:v1:, transit_rt:idx:stop:, transit_rt:idx:route:, transit_rt:source)
# und namespace="vbb:" den getrennten transit_rt:vbb:-Keyspace (quick-260707-kzd:
# Lizenz-/ID-Raum-Trennung VBB CC-BY vs. gtfs.de/DELFI CC-BY-SA, keine trip_id-
# Kollision). Ein Schema-Wechsel kann v1 -> v2 ziehen, ohne Fremd-Keys zu flushen.
_BASE_PREFIX = "transit_rt:"

# Batch-Groesse fuer die Redis-Pipeline in ``store_updates_indexed``. Der
# bundesweite DELFI-GTFS-RT-Feed erzeugt ~300k Redis-Kommandos pro Poller-Tick
# (45s-Kadenz); jedes Kommando einzeln zu awaiten kostet je einen Roundtrip und
# treibt die api-Container-CPU hoch (live gemessen ~138% sustained). Ueber eine
# Pipeline gebuendelt fallen die Roundtrips drastisch. Der Wert 1000 ist ein
# Kompromiss aus moeglichst wenigen Roundtrips und begrenztem Speicher je Batch
# (zu grosse Batches puffern zu viele Kommandos im Client, bevor sie abgehen).
_PIPELINE_BATCH_SIZE = 1000


def parent_stop_id(stop_id: str) -> str | None:
    """Parent-Halt einer DELFI-Steig-ID oder ``None``.

    DELFI-IDs sind ``de:<AGS>:<nr>[:<bereich>[:<steig>]]``; die ersten drei
    Segmente bezeichnen die Station selbst (Parent). Feeds und Clients mischen
    beide Ebenen (gtfs.de-stus meist steiggenau, die statische DELFI-Liste
    liefert Parents bzw. ``::``-Varianten) -> ohne Parent-Bruecke laufen
    Index-Lookups ins Leere (Befund 2026-07-16: no_data trotz vorhandener
    Trips). Numerische gtfs.de-IDs und bereits parent-genaue IDs geben None.
    """
    parts = stop_id.split(":")
    if len(parts) > 3 and parts[0] == "de" and parts[2]:
        return ":".join(parts[:3])
    return None


def _trip_key(trip_id: str, namespace: str = "") -> str:
    return f"{_BASE_PREFIX}{namespace}v1:{trip_id}"


def _stop_idx_key(stop_id: str, namespace: str = "") -> str:
    return f"{_BASE_PREFIX}{namespace}idx:stop:{stop_id}"


def _route_idx_key(route_id: str, namespace: str = "") -> str:
    return f"{_BASE_PREFIX}{namespace}idx:route:{route_id}"


def _source_key(namespace: str = "") -> str:
    # Provenance des aktuell in Redis liegenden RT-Stands (DATA-34/Mobilithek-
    # Switch): welcher Feed hat die letzten Updates geliefert ("mobilithek_delfi"
    # Primär, "gtfs_de" Backup-Fallback ODER "vbb" im VBB-Keyspace). Der Read-Pfad
    # wählt daraus die korrekte Attribution.
    return f"{_BASE_PREFIX}{namespace}source"


async def store_updates_indexed(
    redis,
    updates,
    *,
    ttl: int = 90,
    trip_route_index: dict | None = None,
    namespace: str = "",
) -> None:
    """Schreibt kompakte Trip-Updates indiziert in Redis (NIE den rohen Feed).

    Je Update: ``transit_rt:v1:{trip_id}`` als orjson-Wert (SET mit ex=ttl) plus
    die Sekundär-Indizes ``idx:stop:{stop_id}`` (je Halt) und
    ``idx:route:{route_id}`` (falls route_id vorhanden) als Set der betroffenen
    trip_ids, ebenfalls mit TTL (via expire). NUR kompakte dicts; der rohe
    Feed-Body wird hier bewusst nie gespeichert (Anti-Pattern).

    Audit-Fix K7 (2026-06-29): Im echten gtfs.de-Feed ist ``trip.route_id``
    durchgehend leer, sodass der ``idx:route:``-Index nie befüllt wurde und
    ``live_transit_route_status`` IMMER ``no_data`` lieferte. Mit
    ``trip_route_index`` (``{trip_id: route_id}`` aus der statischen GTFS, vom
    Poller via ``resolver.build_trip_route_index`` gebaut) wird eine fehlende
    route_id über die ``trip_id`` aufgelöst, BEVOR indiziert wird. Die
    aufgelöste route_id wird auch ins gespeicherte Update geschrieben, damit der
    Read-Pfad sie sieht. Ist der Index leer/die trip_id unbekannt, bleibt es
    ehrlich ohne Index (no_data für diesen Trip), aber ohne Crash.

    Performance (quick-260711-l0g): Die Kommandos werden über eine Redis-Pipeline
    gebatcht (``pipe.execute()`` je ``_PIPELINE_BATCH_SIZE`` gequeuten Kommandos
    plus ein finaler Rest-execute), statt jedes einzelne Kommando zu awaiten. Das
    vermeidet die teuren Einzel-Roundtrips bei ~300k Kommandos pro Poller-Tick.
    Das Datenlayout, die Keys, die TTLs und die logische Reihenfolge je Update
    bleiben identisch (verhaltensgleich).
    """
    pipe = redis.pipeline(transaction=False)
    queued = 0

    async def _flush_if_full() -> None:
        # Sendet den bisher gequeuten Batch, sobald die Batch-Groesse erreicht
        # ist, und startet eine frische Pipeline. So bleibt der Client-Speicher
        # je Batch begrenzt, auch wenn deutlich mehr als eine Batch-Groesse an
        # Kommandos anfaellt (mehrere execute-Runden).
        nonlocal pipe, queued
        if queued >= _PIPELINE_BATCH_SIZE:
            await pipe.execute()
            pipe = redis.pipeline(transaction=False)
            queued = 0

    for update in updates:
        trip_id = update.get("trip_id")
        if not trip_id:
            continue

        route_id = update.get("route_id")
        # Audit-Fix K7: leere route_id aus der statischen GTFS auflösen.
        if not route_id and trip_route_index:
            resolved = trip_route_index.get(trip_id)
            if resolved:
                route_id = resolved
                update["route_id"] = resolved

        # Kompaktes dict orjson-serialisiert (NIE der rohe Feed-Body). Gequeuet,
        # nicht awaitet: der Batch geht als Ganzes via pipe.execute() ab.
        pipe.set(_trip_key(trip_id, namespace), orjson.dumps(update), ex=ttl)
        queued += 1
        await _flush_if_full()

        if route_id:
            route_key = _route_idx_key(route_id, namespace)
            pipe.sadd(route_key, trip_id)
            queued += 1
            await _flush_if_full()
            pipe.expire(route_key, ttl)
            queued += 1
            await _flush_if_full()

        for stu in update.get("stop_time_updates", []) or []:
            stop_id = stu.get("stop_id")
            if not stop_id:
                continue
            stop_key = _stop_idx_key(stop_id, namespace)
            pipe.sadd(stop_key, trip_id)
            queued += 1
            await _flush_if_full()
            pipe.expire(stop_key, ttl)
            queued += 1
            await _flush_if_full()
            # Parent-Bruecke (Befund 2026-07-16): steiggenaue stus zusaetzlich
            # unter der Parent-Station indexieren, damit Clients mit der
            # statischen DELFI-Parent-ID (z.B. de:09162:5) die Trips finden.
            # Kostet je steiggenauem stu 2 zusaetzliche Pipeline-Kommandos;
            # die Batch-Pipeline (s.o.) traegt das.
            parent = parent_stop_id(stop_id)
            if parent:
                parent_key = _stop_idx_key(parent, namespace)
                pipe.sadd(parent_key, trip_id)
                queued += 1
                await _flush_if_full()
                pipe.expire(parent_key, ttl)
                queued += 1
                await _flush_if_full()

    # Finaler Rest: alle noch gequeuten Kommandos flushen.
    if queued:
        await pipe.execute()


async def store_rt_source(
    redis, source: str, *, ttl: int = 90, namespace: str = ""
) -> None:
    """Merkt die Quelle des aktuellen RT-Stands (Provenance für die Attribution)."""
    await redis.set(_source_key(namespace), source, ex=ttl)


async def read_rt_source(redis, *, namespace: str = "") -> str | None:
    """Liest die Provenance des aktuellen RT-Stands (oder ``None`` bei Miss)."""
    raw = await redis.get(_source_key(namespace))
    if raw is None:
        return None
    return raw.decode() if isinstance(raw, bytes) else str(raw)


async def get_trip_update(redis, trip_id: str, *, namespace: str = "") -> dict | None:
    """Liest das kompakte Update einer ``trip_id`` (oder ``None`` bei Miss)."""
    raw = await redis.get(_trip_key(trip_id, namespace))
    if raw is None:
        return None
    return orjson.loads(raw)


async def trips_for_stop(redis, stop_id: str, *, namespace: str = "") -> list[str]:
    """Liefert die trip_ids, die einen Halt bedienen (oder leere Liste)."""
    members = await redis.smembers(_stop_idx_key(stop_id, namespace))
    return list(members)


async def trips_for_route(redis, route_id: str, *, namespace: str = "") -> list[str]:
    """Liefert die trip_ids einer Linie (oder leere Liste)."""
    members = await redis.smembers(_route_idx_key(route_id, namespace))
    return list(members)
