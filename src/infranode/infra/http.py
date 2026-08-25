"""Gepoolter httpx-AsyncClient (RES-01) + descriptive User-Agent (RES-05).

Analog zum ``infra/redis.py``-create/close-Paar: genau EIN ``httpx.AsyncClient``
bedient alle Upstreams. Der Client wird im Lifespan-Startup erzeugt
(``create_http_client``) und im Shutdown via ``close_http_client`` geschlossen.
Pool-Limits und ein konservativer Default-Timeout schützen vor hängenden
Upstreams; per-Source-Timeout ist je Request überschreibbar
(``per_source_timeout``), ohne den Pool zu vervielfachen. Der User-Agent trägt
"InfraNode" plus Repo-URL auf JEDEM Request (Fair-Use, T-03-04).
"""

from __future__ import annotations

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from infranode import __version__

#: Nur idempotente Methoden werden wiederholt. Ein POST/PUT/PATCH/DELETE darf sich
#: beim Retry NICHT verdoppeln (kein doppelter Schreib-/Nebeneffekt-Call).
_RETRY_METHODS = frozenset({"GET", "HEAD"})

#: Transiente Upstream-Statuscodes, die einen erneuten Versuch rechtfertigen
#: (voruebergehende Server-/Gateway-Fehler). 4xx (404/429) NICHT: die sind
#: deterministisch und ein Retry wuerde nur Last erzeugen.
_RETRY_STATUS = frozenset({502, 503, 504})

#: Transiente Transport-Ausnahmen (Verbindungs-/Lesetimeouts), die geglaettet
#: werden sollen. Andere httpx-Fehler werden NICHT wiederholt.
_RETRY_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.PoolTimeout,
)


class _TransientStatusError(Exception):
    """Interner Marker: eine transiente Statusantwort (502/503/504) soll retryen.

    Wird NUR innerhalb der Retry-Schleife geworfen, um einen transienten
    Statuscode wie eine transiente Ausnahme behandeln zu koennen. Nach dem letzten
    Versuch wird die getragene Antwort ehrlich zurueckgegeben (nicht eskaliert),
    damit der Aufrufer (resilience/client.py) sie wie bisher als 503 mappen bzw.
    per stale-on-error abfangen kann.
    """

    def __init__(self, response: httpx.Response) -> None:
        self.response = response


class RetryTransport(httpx.AsyncHTTPTransport):
    """httpx-Transport mit zentralem tenacity-Retry fuer idempotente GET/HEAD.

    Wiederholt einen Request maximal 3x gesamt (2 Retries) bei transienten
    Transport-Ausnahmen ODER transienten Statuscodes (502/503/504), aber
    ausschliesslich fuer idempotente Methoden (GET/HEAD). Nicht-idempotente
    Methoden und 4xx-Antworten werden unveraendert einmal durchgereicht.

    Latenz-Budget (bewusst klein gehalten): der Default read-timeout betraegt 5s
    je Versuch (infra/http.create_http_client); der Backoff ist 0.2s, dann 0.4s.
    Worst-Case bei einem durchgehend toten Upstream: ~ 3x5s Timeout + 0.6s Backoff
    ~ 15.6s, aber NUR fuer eine ohnehin sterbende Quelle, die anschliessend in den
    Circuit-Breaker/stale-on-error-Pfad faellt. Bei gesunden Requests entsteht
    KEINE Zusatzlatenz: ein erfolgreicher erster Versuch kehrt sofort zurueck; nur
    transiente Aussetzer werden geglaettet.
    """

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # Nicht-idempotente Methoden: kein Retry (POST/PUT/PATCH/DELETE einmalig).
        if request.method not in _RETRY_METHODS:
            return await super().handle_async_request(request)

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=0.2, max=0.4),
                retry=retry_if_exception_type(
                    (*_RETRY_EXCEPTIONS, _TransientStatusError)
                ),
                reraise=True,
            ):
                with attempt:
                    response = await super().handle_async_request(request)
                    if response.status_code in _RETRY_STATUS:
                        # Transienter Status -> als Ausnahme werfen, um den naechsten
                        # Versuch auszuloesen; letzte Antwort wird unten zurueckgegeben.
                        raise _TransientStatusError(response)
                    return response
        except _TransientStatusError as exc:
            # Alle Versuche erschoepft, letzter war ein transienter Status: die
            # letzte Antwort ehrlich zurueckgeben statt als RetryError zu eskalieren
            # (der Aufrufer entscheidet ueber 503/stale-on-error wie bisher).
            return exc.response
        # Unerreichbar (die Schleife kehrt via return zurueck oder reraist eine
        # transiente Transport-Ausnahme), aber mypy/ruff-freundlicher Fallback:
        raise RuntimeError("RetryTransport: unerreichbarer Pfad")  # pragma: no cover


#: Descriptive User-Agent auf JEDEM Upstream-Request (RES-05, T-03-04). Die Version
#: stammt aus der einzigen Quelle ``infranode.__version__`` (kein hartkodierter
#: Versionsstring, der mit Releases driftet).
USER_AGENT = (
    f"InfraNodeAPI/{__version__} "
    "(+https://github.com/street1983nk/infranode-api; open data proxy)"
)

#: Prozessweiter Pool-Singleton. ``create_http_client`` gibt für denselben
#: Prozess dieselbe Instanz zurück (geteilter Connection-Pool, RES-01).
_client: httpx.AsyncClient | None = None


def create_http_client(settings) -> httpx.AsyncClient:
    """Liefert den prozessweiten, gepoolten AsyncClient (RES-01/05).

    Beim ersten Aufruf wird der Client gebaut und gemerkt; Folgeaufrufe liefern
    dieselbe Instanz (ein geteilter Pool, kein Client pro Request). Wurde der
    gemerkte Client zwischenzeitlich geschlossen (Lifespan-Shutdown), wird ein
    frischer gebaut. Synchron (kein await beim Bau).
    """
    global _client
    if _client is None or _client.is_closed:
        user_agent = getattr(settings, "http_user_agent", None) or USER_AGENT
        limits = httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=30.0,
        )
        # Zentraler Retry-Transport (Quick-260709-huj): glaettet transiente
        # Upstream-Aussetzer fuer idempotente GET/HEAD. Die Pool-Limits werden am
        # Transport gesetzt (bei explizitem transport= ignoriert der Client sein
        # eigenes limits=-Argument), Timeout/UA/follow_redirects bleiben am Client.
        _client = httpx.AsyncClient(
            headers={"User-Agent": user_agent},  # RES-05: UA auf JEDEM Request
            transport=RetryTransport(limits=limits),
            # Konservativer Default; per-Source per Request überschreibbar (T-03-03).
            timeout=httpx.Timeout(connect=2.0, read=5.0, write=5.0, pool=1.0),
            # KEINE automatischen Redirects (Audit MEDIUM-1, 2026-06-10): die
            # SSRF-Invariante der Adapter (hartkodierte Hosts/Allowlists) schützt
            # nur den ERSTEN Request; ein 30x eines (kompromittierten) Upstreams
            # würde sonst blind verfolgt, auch auf interne Ziele (Metadaten-IP,
            # redis). Ein legitimer Redirect schlägt jetzt als Fehler durch und
            # fällt in der Beta im Smoke/Monitoring auf; der betroffene Adapter
            # zieht dann gezielt auf die finale URL nach.
            follow_redirects=False,
        )
    return _client


def per_source_timeout(settings, *, source: str) -> httpx.Timeout:
    """Liefert den per-Source-Timeout, der den Client-Default je Request überschreibt.

    Der Pool bleibt EIN Singleton; nur der Timeout variiert je Quelle (eine
    träge Quelle wie Wikidata-SPARQL darf länger lesen als eine schnelle
    REST-Quelle, Pitfall 5).
    Quellenspezifische Werte kommen ab Phase 4 aus ``SourceConfig``; bis dahin
    gilt der konservative Default.
    """
    return httpx.Timeout(connect=2.0, read=5.0, write=5.0, pool=1.0)


async def close_http_client(client: httpx.AsyncClient | None) -> None:
    """Schliesst den gepoolten Client samt Pool sauber (no-op bei None)."""
    global _client
    if client is not None:
        await client.aclose()
    _client = None
