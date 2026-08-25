"""Hintergrund-Poller für GTFS-RT (Phase 19, Plan 04, RESEARCH Pattern 1).

Der Poller parst den GTFS-RT-Feed (~68 MB) EINMAL je Kadenz und legt die kompakten,
indizierten Updates in Redis ab (``transit/store.store_updates_indexed``). Der
Request-Pfad liest danach NUR aus Redis (kein 68-MB-Parse pro Request, kein
CPU-Spike/OOM auf der 4-GB-Box, T-19-REQPARSE). Der Poller läuft als langlebiger
asyncio-Task im Lifespan (``main.py`` ``_schedule``/``bg_tasks``), NIE im
Request-Pfad.

Robustheit: eine Iteration, die mit einer Exception scheitert (Upstream down,
Parse-Fehler), darf den Task NICHT crashen - sie wird geloggt (``log.warning``),
und nach ``interval_s`` Sekunden läuft die nächste Iteration. ``CancelledError``
(Shutdown im Lifespan-finally) wird durchgereicht (sauberes Beenden).
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime

import structlog

from infranode.adapters.gtfs_rt import fetch_gtfs_rt_feed, parse_trip_updates
from infranode.transit.resolver import build_trip_route_index
from infranode.transit.store import store_rt_source, store_updates_indexed

log = structlog.get_logger()


def _gtfs_static_path_for(
    settings, used_source: str | None, namespace: str = ""
) -> str | None:
    """Waehlt den statischen GTFS-Pfad passend zur RT-Provenance (Audit-Fix K7).

    Analog ``api/v1/live.live_transit_trip``: liefert aktuell der DELFI-Feed
    (``mobilithek_delfi``), werden die DELFI-IDs gegen ``delfi_gtfs_path``
    aufgelöst (Fallback ``gtfs_rt_static_path``); beim gtfs.de-Backup umgekehrt.
    So passen ID-Namensraum (trip_id) und Statik zusammen. ``None`` -> keine
    Statik konfiguriert (route_id bleibt ehrlich unaufgelöst, kein Crash).

    quick-260707-kzd: im VBB-Keyspace (``namespace == "vbb:"``) hat der VBB-Feed
    seinen EIGENEN ID-Raum; die Anreicherung nutzt darum ausschliesslich
    ``vbb_gtfs_static_path`` (nie die DELFI-/gtfs.de-Statik, sonst mischen sich
    die ID-Raeume). Ist er ``None``, bleibt die Anreicherung ehrlich aus.
    """
    if namespace == "vbb:":
        return getattr(settings, "vbb_gtfs_static_path", None)
    if used_source == "mobilithek_delfi":
        return getattr(settings, "delfi_gtfs_path", None) or getattr(
            settings, "gtfs_rt_static_path", None
        )
    return getattr(settings, "gtfs_rt_static_path", None) or getattr(
        settings, "delfi_gtfs_path", None
    )


def _load_trip_route_index(cache: dict, path: str | None) -> dict | None:
    """Baut/cached die ``{trip_id: route_id}``-Map je Statik-Pfad (Audit-Fix K7).

    ``trips.txt`` ist klein; der Index wird je Pfad EINMAL gebaut und im
    ``cache`` (pro Poller-Lauf gehalten) wiederverwendet, statt ihn jeden Tick
    (45s) neu von Platte zu streamen. Ein Lese-/Parse-Fehler ODER ein fehlender
    Pfad -> ``None`` (ehrlich, kein Crash; route_id bleibt unaufgelöst).
    """
    if not path:
        return None
    if path in cache:
        return cache[path]
    try:
        index = build_trip_route_index(path)
    except (OSError, KeyError, ValueError) as exc:
        log.warning("gtfs_rt_static_index_failed", error=str(exc), path=path)
        index = None
    cache[path] = index
    return index


async def _fetch_with_fallback(
    app, *, source: str, abo_id: str | None
) -> tuple[bytes | None, str | None]:
    """Holt den RT-Feed und fällt von ``mobilithek_delfi`` auf ``gtfs_de`` zurück.

    Primärquelle ``mobilithek_delfi`` (DELFI über Mobilithek-mTLS): liefert sie
    keine Bytes (no_data/disabled) ODER scheitert sie (Upstream-Fehler), wird der
    keylose gtfs.de-Backup-Feed gezogen ("schalte um und gtfs als backup"). Gibt
    ``(body, used_source)`` zurück, damit der Read-Pfad die korrekte Attribution
    (DELFI e.V. vs gtfs.de) wählen kann. Andere Quellen (gtfs_de) ohne Fallback.
    """
    http = app.state.http
    mtls = getattr(app.state, "mobilithek_http", None)
    if source == "mobilithek_delfi":
        try:
            feed = await fetch_gtfs_rt_feed(
                http, mtls, source="mobilithek_delfi", abo_id=abo_id
            )
        except Exception as exc:
            log.warning("gtfs_rt_delfi_failed_fallback_gtfs_de", error=str(exc))
            feed = None
        if feed is not None:
            return feed, "mobilithek_delfi"
        # Backup: keyloser gtfs.de-Feed (raise_for_status fängt die Außenschleife).
        feed = await fetch_gtfs_rt_feed(http, None, source="gtfs_de", abo_id=None)
        return feed, "gtfs_de"

    feed = await fetch_gtfs_rt_feed(http, mtls, source=source, abo_id=abo_id)
    return feed, source


async def gtfs_rt_poller(
    app,
    *,
    interval_s: int = 45,
    source: str,
    abo_id: str | None,
    settings=None,
    namespace: str = "",
    lock_key: str = "lock:gtfs_rt_poll",
    heartbeat_key: str = "heartbeat:gtfs_rt",
) -> None:
    """Endlosschleife: holt+parst den Feed je Kadenz und legt ihn nach Redis.

    Je Iteration: ``fetch_gtfs_rt_feed`` -> bei ``None`` (no_data/disabled) wird
    der Store übersprungen; bei ``bytes`` -> ``parse_trip_updates`` ->
    ``store_updates_indexed``. Eine Exception in einer Iteration crasht den Task
    NICHT (``log.warning``, weiter nach ``asyncio.sleep(interval_s)``).
    ``CancelledError`` (Shutdown) wird durchgereicht.

    Audit-Fix K7: aus ``settings`` wird je Provenance der statische GTFS-Pfad
    bestimmt und daraus ein ``{trip_id: route_id}``-Index gebaut (pro Pfad
    gecached), damit ``store_updates_indexed`` leere route_ids auflösen kann.

    quick-260707-kzd: ``namespace``/``lock_key``/``heartbeat_key`` sind additiv
    keyword-only mit den heutigen Defaults (leerer Namespace, die bestehenden
    Lock-/Heartbeat-Keys), damit der Bestands-Poller verhaltensgleich bleibt. Der
    VBB-Poller ruft dieselbe Schleife mit ``namespace="vbb:"``, eigenem Lock
    (``lock:gtfs_rt_poll:vbb``) und eigenem Heartbeat (``heartbeat:gtfs_rt:vbb``);
    so schreibt er in den isolierten transit_rt:vbb:-Keyspace und setzt genau die
    Marker, die der Watchdog fuer 'vbb' kennt.
    """
    # Audit-Fix K7: Index-Cache je Statik-Pfad (überlebt die Ticks; trips.txt
    # ändert sich nur beim wöchentlichen Statik-Refresh).
    index_cache: dict = {}
    while True:
        try:
            # Multi-Worker-Guard: bei uvicorn --workers läuft dieser Poller in
            # JEDEM Worker. Ein per-Tick Redis-Lock (SET NX EX) stellt sicher, dass
            # pro Intervall nur EIN Worker tatsächlich pollt (kein redundanter
            # Upstream-Fetch). TTL < interval -> läuft vor dem nächsten Tick ab;
            # fällt der Halter aus, übernimmt nächsten Tick ein anderer Worker
            # (selbstheilend, kein dauerhafter Leader). Redis-Fehler -> poll
            # trotzdem (Graceful Degradation, nie Crash).
            should_poll = True
            try:
                should_poll = bool(
                    await app.state.redis.set(
                        lock_key,
                        b"1",
                        nx=True,
                        ex=max(1, interval_s - 5),
                    )
                )
            except Exception:
                should_poll = True
            if should_poll:
                feed, used_source = await _fetch_with_fallback(
                    app, source=source, abo_id=abo_id
                )
                if feed is not None:
                    updates = parse_trip_updates(feed)
                    # Audit-Fix K7: route_id aus der zur Provenance passenden
                    # statischen GTFS auflösen (Index pro Pfad gecached).
                    trip_route_index = None
                    if settings is not None:
                        static_path = _gtfs_static_path_for(
                            settings, used_source, namespace
                        )
                        trip_route_index = _load_trip_route_index(
                            index_cache, static_path
                        )
                    await store_updates_indexed(
                        app.state.redis,
                        updates,
                        ttl=90,
                        trip_route_index=trip_route_index,
                        namespace=namespace,
                    )
                    # Provenance des Stands für die Read-Pfad-Attribution.
                    await store_rt_source(
                        app.state.redis,
                        used_source or source,
                        ttl=90,
                        namespace=namespace,
                    )
        except asyncio.CancelledError:
            # Shutdown (Lifespan-finally cancelt die bg_tasks): sauber beenden.
            raise
        except Exception as exc:
            log.warning("gtfs_rt_poll_failed", error=str(exc), source=source)
        # Heartbeat: Watchdog (check_pollers) liest bevorzugt heartbeat_key.
        # Vorfall 2026-08-01 (CRITICAL poller:gtfs_rt nach dem Doppel-Deploy):
        # der Heartbeat wurde nur nach ERFOLGREICHEM Store gesetzt, damit mass
        # check_pollers "letzter erfolgreicher Tick < 135s" statt "Task lebt",
        # und jeder kurze Upstream-Ausfall ueber ~2 Ticks wurde zum Fehlalarm
        # samt Deadman-Block. Jetzt bezeugt der Heartbeat JEDE Iteration (auch
        # eine fehlgeschlagene): ein echter Poller-Tod (Crash, nie gestartet)
        # setzt ihn weiterhin nicht. Veraltete DATEN meldet nicht dieser Key,
        # sondern die Stale-Fenster-/no_data-Semantik des Read-Pfads
        # (transit_rt:source, TTL 90s, wird unveraendert nur bei Erfolg gesetzt).
        # Muster des Lock-set: bare except -> graceful, nie Crash der Schleife.
        # Heartbeat nie crash-kritisch -> Redis-Fehler unterdruecken.
        with contextlib.suppress(Exception):
            await app.state.redis.set(
                heartbeat_key,
                datetime.now(UTC).isoformat(),
                ex=3 * interval_s,
            )
        await asyncio.sleep(interval_s)


def maybe_start_gtfs_rt_poller(app, settings, schedule) -> None:
    """Startet den Poller-Task NUR bei aktivem Toggle + auflösbarer Quelle.

    Auflösbarkeit (RESEARCH Pattern 7):
    - ``enable_gtfs_rt`` muss True sein,
    - Quelle ``gtfs_de``: immer auflösbar (keylos),
    - Quelle ``mobilithek_delfi``: nur mit mTLS-Client (``app.state.mobilithek_http``)
      UND ``transit_rt_delfi_abo_id`` (Settings-Allowlist, SSRF) - sonst kein Task
      (Graceful Degradation = disabled).

    Bei deaktiviertem Toggle (Default) wird KEIN Task erzeugt (bg_tasks
    unverändert), der bestehende App-Start bleibt unverändert.
    """
    if not getattr(settings, "enable_gtfs_rt", False):
        # Default-Zustand (Toggle aus) ist KEIN Fehler -> info, nicht warning.
        log.info("gtfs_rt_poller_not_started", reason="toggle_disabled")
        return

    source = getattr(settings, "transit_rt_source", "gtfs_de")
    abo_id = getattr(settings, "transit_rt_delfi_abo_id", None)

    if source == "mobilithek_delfi":
        mobilithek_http = getattr(app.state, "mobilithek_http", None)
        if mobilithek_http is None:
            # Toggle an, aber kein mTLS-Client (Cert fehlt/defekt) -> laut warnen.
            log.warning(
                "gtfs_rt_poller_not_started", reason="mobilithek_client_missing"
            )
            return
        if not abo_id:
            # Cert vorhanden, aber Abo-ID fehlt (Settings-Allowlist) -> laut warnen.
            log.warning("gtfs_rt_poller_not_started", reason="abo_id_missing")
            return

    log.info("gtfs_rt_poller_started", source=source, interval_s=45)
    schedule(
        gtfs_rt_poller(
            app, interval_s=45, source=source, abo_id=abo_id, settings=settings
        )
    )


def maybe_start_vbb_poller(app, settings, schedule) -> None:
    """Startet den keylosen VBB-Berlin-Poller NUR bei aktivem ``enable_vbb`` (kzd).

    VBB ist keylos (kein Cert/Abo noetig, anders als mobilithek_delfi), daher genuegt
    das Toggle-Gate. Bei aus (Default) wird KEIN Task erzeugt und das Verhalten
    aendert sich in keiner Weise (info, kein Fehler). Bei an laeuft dieselbe
    ``gtfs_rt_poller``-Schleife mit ``source="vbb"``, ``abo_id=None``,
    ``namespace="vbb:"``, eigenem Lock (``lock:gtfs_rt_poll:vbb``) und eigenem
    Heartbeat (``heartbeat:gtfs_rt:vbb``). ``settings`` wird durchgereicht, damit die
    optionale Statik-Anreicherung ueber ``vbb_gtfs_static_path`` greift (ist der Pfad
    None, bleiben route_short_name/trip_headsign ehrlich unaufgeloest, kein Crash).
    Der VBB-Poller schreibt transit_rt:vbb:source (je Tick) und heartbeat:gtfs_rt:vbb,
    GENAU die Marker, die in ops/watchdog.py fuer "vbb" registriert sind -> der
    Watchdog eskaliert einen still ausgefallenen VBB-Poller (Silent-Failure-Alarm).
    """
    if not getattr(settings, "enable_vbb", False):
        # Default-Zustand (Toggle aus) ist KEIN Fehler -> info, nicht warning.
        log.info("vbb_poller_not_started", reason="toggle_disabled")
        return

    log.info("vbb_poller_started", source="vbb", interval_s=45)
    schedule(
        gtfs_rt_poller(
            app,
            interval_s=45,
            source="vbb",
            abo_id=None,
            settings=settings,
            namespace="vbb:",
            lock_key="lock:gtfs_rt_poll:vbb",
            heartbeat_key="heartbeat:gtfs_rt:vbb",
        )
    )
