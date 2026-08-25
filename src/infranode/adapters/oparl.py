"""Generischer keyloser OParl-1.x-Adapter für kommunale Ratsinformationen.

Zieht OParl-1.x-"Paper"-Objekte (Vorlagen, Anträge, Beschlüsse) der
Ratsinformationssysteme der acht lizenzgeklärten Städte (Dresden, Köln,
Düsseldorf, Münster, Leipzig, Magdeburg, Osnabrück, Freiburg im Breisgau)
über httpx-JSON. Reiner I/O + defensives Parsen:
KEINE Stadt-Zuordnung, KEIN Store, KEIN Mapping (das liegt im Ingest bzw. im
Mapper). Vorbild-Härtungen aus ``adapters.oeffentlichevergabe``:

Sicherheit:

- **SSRF (Spoofing):** Jede abgerufene Ziel-URL MUSS host-mässig zu einem der
  ``system_url``-Hosts aus ``COUNCIL_CITIES`` gehören (Host-Allowlist, geprüft
  VOR jedem ``http.get``). Paginierte ``links.next``-URLs (OParl external lists
  liefern absolute Next-URLs) werden ebenfalls gegen die Allowlist geprüft; ein
  Host ausserhalb -> Abbruch (kein Request).
- **PARSE (Denial of Service):** Jede Antwort wird defensiv geparst (kaputtes
  JSON -> leere Liste, kein Crash); jedes OParl-Feld wird mit None-Fallback
  gelesen (kein ungefangener KeyError).
- **DOS (Paginierung):** ``max_pages`` deckelt die Zahl gezogener Listen-Seiten;
  ohne Deckel läuft die Paginierung bis ``links.next`` erschöpft ist.

``COUNCIL_CITIES`` ist fail-closed: NUR die acht lizenzgeklärten Städte, keine
weiteren. ``papers_url`` dient als Fallback/Doku, wenn die Laufzeit-Auflösung
über das System-Objekt scheitert (Task: bevorzugt zur Laufzeit auflösen).
"""

from __future__ import annotations

import asyncio
from urllib.parse import urlsplit

import httpx

from infranode.infra.http import USER_AGENT

# Fail-closed: NUR die acht lizenzgeklärten Städte (Dresden, Köln, Düsseldorf,
# Münster, Leipzig, Magdeburg, Osnabrück, Freiburg im Breisgau).
# ``system_url`` ist der OParl-System-Einstieg, ``papers_url``
# der Fallback auf die Papers-Liste (None = ausschliesslich zur Laufzeit über das
# body-Objekt auflösen). Keine weiteren Städte ohne erneute Lizenzklärung.
COUNCIL_CITIES: dict[str, dict[str, str | None]] = {
    "dresden": {
        "system_url": "https://oparl.dresden.de/system",
        "papers_url": "https://oparl.dresden.de/bodies/0001/papers",
    },
    "koeln": {
        "system_url": "https://buergerinfo.stadt-koeln.de/oparl/system",
        "papers_url": (
            "https://buergerinfo.stadt-koeln.de/oparl/bodies/"
            "stadtverwaltung_koeln/papers"
        ),
    },
    "duesseldorf": {
        "system_url": "https://ris-oparl.itk-rheinland.de/Oparl/system",
        # Zur Laufzeit aus dem body-Objekt auflösen (kein stabiler Papers-Pfad).
        "papers_url": None,
    },
    "muenster": {
        "system_url": "https://oparl.stadt-muenster.de/system",
        # Zur Laufzeit auflösen.
        "papers_url": None,
    },
    "leipzig": {
        "system_url": (
            "https://ratsinformation.leipzig.de/allris_leipzig_public/oparl/system"
        ),
        "papers_url": (
            "https://ratsinformation.leipzig.de/allris_leipzig_public/oparl/"
            "papers?body=2387"
        ),
    },
    # Nord-Ergaenzung 2026-07-17 (Lizenz je System-Objekt verifiziert): Magdeburg
    # (SOMACOS, DL-DE/Zero) + Osnabrueck (ALLRIS, CC-BY-4.0). papers_url zur
    # Laufzeit ueber das body-Objekt aufloesen (kein stabiler Papers-Pfad).
    "magdeburg": {
        "system_url": "https://ratsinfo.magdeburg.de/oparl/system",
        "papers_url": None,
    },
    "osnabrueck": {
        "system_url": "https://www.osnabrueck.sitzung-online.de/oparl/system",
        "papers_url": None,
    },
    # Freiburg 2026-08-01 (Lizenz per Mail vom Ratsbuero bestaetigt): more!
    # software/RUBIN. Der Papers-Pfad ist stabil und paginiert ueber
    # ``links.next`` auf demselben Host; als Fallback hinterlegt.
    "freiburg-im-breisgau": {
        "system_url": "https://ris.freiburg.de/oparl/system",
        "papers_url": "https://ris.freiburg.de/oparl/body/FR/paper",
    },
}

# Host-Allowlist (SSRF): die Hosts aller konfigurierten system_url. Jede Ziel-URL
# (System, Body, Papers-Liste, links.next) MUSS zu einem dieser Hosts gehören.
_ALLOWED_HOSTS: frozenset[str] = frozenset(
    urlsplit(str(c["system_url"])).netloc for c in COUNCIL_CITIES.values()
)

_HEADERS = {"User-Agent": USER_AGENT}


def _host_allowed(url: str | None) -> bool:
    """True, wenn ``url`` (absolut, https) zu einem Allowlist-Host gehört (SSRF)."""
    if not isinstance(url, str) or not url.strip():
        return False
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https"):
        return False
    return parts.netloc in _ALLOWED_HOSTS


def _force_https(url: str) -> str:
    """Hebt eine Allowlist-URL auf https an (plain http wird NIE angefragt).

    Dresden liefert links.next mit http://-Schema; der Client folgt Redirects
    nicht, ein 301 wirkt dann wie ein Listenende (Backfill brach nach Seite 1
    ab). Alle Allowlist-Hosts sprechen https.
    """
    stripped = url.strip()
    if stripped.startswith("http://"):
        return "https://" + stripped[len("http://") :]
    return stripped


async def _get_json(http: httpx.AsyncClient, url: str) -> dict | None:
    """Holt ``url`` als JSON-Objekt, defensiv (SSRF-Guard + None bei Fehler).

    Prüft die Host-Allowlist VOR dem Request (SSRF); ein Host ausserhalb -> None
    (kein Request). Ein Nicht-200/kaputtes JSON/nicht-dict-Body -> None (kein
    Crash, PARSE-Härtung).
    """
    if not _host_allowed(url):
        return None
    try:
        resp = await http.get(_force_https(url), headers=_HEADERS)
        resp.raise_for_status()
        obj = resp.json()
    except (httpx.HTTPError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


async def resolve_papers_url(http: httpx.AsyncClient, city: str) -> str | None:
    """Löst die Papers-Listen-URL EINER Stadt über das OParl-System auf.

    Liest ``system_url``, folgt zum ersten body (``system.body`` als Liste ODER
    externe ``bodies``-Liste), liest dort ``body.paper`` (die Papers-Listen-URL).
    Scheitert die Auflösung (System nicht erreichbar, kein body, kein paper-Feld,
    Host ausserhalb der Allowlist), fällt sie auf ``COUNCIL_CITIES[city]["papers_url"]``
    zurück (robust gegen URL-Wechsel, Task: bevorzugt zur Laufzeit auflösen).

    Unbekannte Stadt -> None (fail-closed).
    """
    cfg = COUNCIL_CITIES.get(city)
    if cfg is None:
        return None
    fallback = cfg.get("papers_url")

    system = await _get_json(http, str(cfg["system_url"]))
    if system is None:
        return fallback

    # OParl-System verweist auf die body-Liste: entweder inline (system.body als
    # Liste von Objekten mit paper-Feld) oder als externe Listen-URL (system.body
    # als String) bzw. das ältere system.bodies. Defensiv beide Formen abklopfen.
    body_ref = system.get("body")
    first_body: dict | None = None

    if isinstance(body_ref, list) and body_ref:
        first = body_ref[0]
        if isinstance(first, dict):
            first_body = first
    if first_body is None:
        # body/bodies als externe Listen-URL -> nachladen und ersten Eintrag nehmen.
        list_url = None
        if isinstance(body_ref, str):
            list_url = body_ref
        elif isinstance(system.get("bodies"), str):
            list_url = system.get("bodies")
        if list_url:
            body_list = await _get_json(http, list_url)
            if body_list is not None:
                data = body_list.get("data")
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    first_body = data[0]

    if first_body is not None:
        paper_url = first_body.get("paper")
        if isinstance(paper_url, str) and _host_allowed(paper_url):
            return _force_https(paper_url)

    return fallback


async def iter_papers(
    http: httpx.AsyncClient,
    city: str,
    *,
    start_url: str | None = None,
    created_since: str | None = None,
    modified_since: str | None = None,
    max_pages: int | None = None,
):
    """Async-Generator: yieldet ``(papers_der_seite, next_url)`` je OParl-Listen-Seite.

    Ermoeglicht seitenweises Schreiben + Resume im Ingest (statt erst die ganze
    Liste im Speicher aufzubauen): ``next_url`` im Yield ist die naechste zu
    holende Seite bzw. ``None``, wenn die Liste erschoepft ist (der Ingest
    persistiert diesen Cursor pro Seite).

    - ``start_url=None`` -> Papers-URL ueber ``resolve_papers_url`` (frischer
      Start; ``created_since``/``modified_since`` werden auf der ERSTEN Seite
      mitgeschickt, nicht alle Systeme unterstuetzen sie -> harter Filter im
      Ingest).
    - ``start_url`` gesetzt (Resume-Cursor) -> dort fortsetzen, OHNE Query-Params
      (die ``links.next``-URL traegt Paginierung/Filter bereits selbst).

    Host-Allowlist (SSRF) + https-Anhebung + defensives Parsen wie gehabt.
    Unaufloesbare Stadt/URL -> gar kein Yield (leer).
    """
    resuming = start_url is not None
    if start_url is None:
        start_url = await resolve_papers_url(http, city)
    if start_url is None:
        return

    params: dict[str, str] = {}
    if created_since is not None:
        params["created_since"] = created_since
    if modified_since is not None:
        params["modified_since"] = modified_since

    next_url: str | None = start_url
    pages = 0
    first_page = not resuming  # beim Resume KEINE Params neu anhaengen

    while next_url is not None:
        if max_pages is not None and pages >= max_pages:
            break
        # Query-Parameter nur auf der ERSTEN Seite eines frischen Starts.
        query = params if (first_page and params) else None
        page = await _fetch_page(http, next_url, query)
        if page is None:
            break
        data = page.get("data")
        page_papers = (
            [item for item in data if isinstance(item, dict)]
            if isinstance(data, list)
            else []
        )
        pages += 1
        first_page = False

        links = page.get("links")
        candidate = links.get("next") if isinstance(links, dict) else None
        # links.next MUSS zur Host-Allowlist gehören (SSRF); sonst Abbruch.
        # Danach Schema auf https anheben (Dresden liefert http://-next-Links).
        nxt = (
            _force_https(candidate)
            if isinstance(candidate, str) and _host_allowed(candidate)
            else None
        )
        yield page_papers, nxt
        next_url = nxt


async def fetch_papers(
    http: httpx.AsyncClient,
    city: str,
    *,
    created_since: str | None = None,
    modified_since: str | None = None,
    max_pages: int | None = None,
) -> list[dict]:
    """Zieht die paginierte OParl-Papers-Liste EINER Stadt als flache Liste.

    Duenner Wrapper ueber ``iter_papers`` (haengt alle Seiten aneinander): fuer
    Aufrufer, die
    die ganze Liste auf einmal brauchen. Unauflösbare Stadt/URL -> leere Liste.
    """
    papers: list[dict] = []
    async for page_papers, _next_url in iter_papers(
        http,
        city,
        created_since=created_since,
        modified_since=modified_since,
        max_pages=max_pages,
    ):
        papers.extend(page_papers)
    return papers


async def _fetch_page(
    http: httpx.AsyncClient, url: str, params: dict[str, str] | None
) -> dict | None:
    """Holt eine Papers-Listen-Seite als JSON-Objekt (SSRF-Guard, defensiv).

    Bis zu 3 Versuche mit kurzem Backoff: ein einzelner transienter Upstream-
    Fehler (Timeout, 5xx) kappte sonst die gesamte restliche Paginierung
    (real: Koeln brach bei Seite 27 von ~950 ab).
    """
    if not _host_allowed(url):
        return None
    target = _force_https(url)
    for attempt in range(3):
        if attempt:
            await asyncio.sleep(2.0 * attempt)
        try:
            resp = await http.get(target, params=params or None, headers=_HEADERS)
            resp.raise_for_status()
            obj = resp.json()
        except (httpx.HTTPError, ValueError):
            continue
        return obj if isinstance(obj, dict) else None
    return None
