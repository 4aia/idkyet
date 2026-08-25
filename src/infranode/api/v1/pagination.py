"""Paginierungs-Verträge (API-04): PageParams + page_params + paginate.

Opt-in Listen-Paginierung (D-07): page/limit/offset + Whitelist für sort/order.
``limit`` wird auf ``MAX_LIMIT`` gedeckelt (200 mit gedeckelter Seite statt 5xx,
Best-Practice #8): der zentrale RequestValidationError-Handler mappt auf 400, ein
überhöhtes limit soll aber NICHT als invalid_request gelten, daher wird in
``page_params`` über ``min(limit, MAX_LIMIT)`` gedeckelt statt über ``le=``
abgewiesen. Whitelist-Verstoß bei sort/order -> ``ValidationFailedError`` (400),
BEVOR roher User-String interpretiert wird (T-11-FILTER-INJ). Offset-Overflow ->
Python-Slice ergibt ``[]`` (200, nie 500, Best-Practice #8).
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query

from infranode.api.errors import ValidationFailedError
from infranode.infra.gpt_actions import is_gpt_action

# Defaults + harte Obergrenze für das Seiten-Limit (Cap via Query(le=MAX_LIMIT)).
DEFAULT_LIMIT = 50
MAX_LIMIT = 200

# Truthy-Werte fuer den kanalunabhaengigen Vollausgabe-Schalter ``?all=...``.
_TRUTHY_VALUES = frozenset({"1", "true", "yes"})


@dataclass
class PageParams:
    """Validierte Paginierungs-Parameter eines Listen-GETs.

    ``limit`` ist ``int | None``: ``None`` bedeutet "unbounded / Vollausgabe"
    (kein oberes Seiten-Limit, nur ``offset`` wirkt). Das ist der kanal-abhaengige
    Default fuer direktes REST (kein Breaking Change fuer Bulk-Nutzer) sowie das
    Ergebnis des ``limit=all``/``?all=1``-Overrides; ein gebundener Kanal
    (GPT-Actions/MCP) bzw. ein explizites numerisches limit traegt hier ein ``int``.
    """

    page: int
    limit: int | None
    offset: int
    sort: str | None
    order: str


def page_params(
    page: int = Query(1, ge=1),
    limit: int = Query(DEFAULT_LIMIT, ge=1),
    offset: int = Query(0, ge=0),
    sort: str | None = Query(None),
    order: str = Query("asc"),
) -> PageParams:
    """FastAPI-Dependency: parst + validiert page/limit/offset/sort/order.

    ``limit`` wird über ``min(limit, MAX_LIMIT)`` gedeckelt (gedeckelte 200-Seite
    statt 5xx/4xx, Best-Practice #8), nicht über ``le=`` hart abgewiesen.
    """
    if order not in ("asc", "desc"):
        raise ValidationFailedError(
            "order muss 'asc' oder 'desc' sein.",
            hint="Erlaubt: asc, desc.",
        )
    limit = min(limit, MAX_LIMIT)
    return PageParams(page=page, limit=limit, offset=offset, sort=sort, order=order)


def paginate(items: list, p: PageParams, *, sort_whitelist: set[str]) -> list:
    """Schneidet eine Seite aus ``items`` (Whitelist-gesichert).

    sort nicht in der Whitelist -> ValidationFailedError(400). Offset-Overflow
    ergibt durch den Python-Slice eine leere Liste (200, nie 500).
    """
    if p.sort and p.sort not in sort_whitelist:
        raise ValidationFailedError(
            f"Unbekanntes sort-Feld '{p.sort}'.",
            hint=f"Erlaubt: {', '.join(sorted(sort_whitelist))}.",
        )
    if p.limit is None:
        # Vollausgabe (REST-Default / limit=all): nur ab offset schneiden, kein
        # oberes Limit; ``(page - 1) * None`` waere ein Typfehler, daher hier nur
        # ``offset`` als Startpunkt (page ist bei Vollausgabe bedeutungslos).
        return items[p.offset :]
    start = p.offset if p.offset else (p.page - 1) * p.limit
    return items[start : start + p.limit]


def _parse_int_param(raw: str | None, *, name: str, minimum: int, default: int) -> int:
    """Parst einen rohen Query-String zu einem int mit Mindestwert (oder Default).

    ``None`` (Parameter nicht gesetzt) -> ``default``. Nicht-numerisch oder unter
    ``minimum`` -> ``ValidationFailedError`` (400 invalid_request), BEVOR der Wert
    in einen Slice-Index gelangt (T-chc-03). Kein roher String erreicht die
    Slice-Semantik.
    """
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValidationFailedError(
            f"Ungueltiger Wert fuer '{name}': '{raw}'.",
            hint=f"'{name}' muss eine ganze Zahl >= {minimum} sein.",
        ) from None
    if value < minimum:
        raise ValidationFailedError(
            f"Ungueltiger Wert fuer '{name}': {value}.",
            hint=f"'{name}' muss eine ganze Zahl >= {minimum} sein.",
        )
    return value


def _is_full_output_override(qp) -> bool:
    """True bei kanalunabhaengigem Vollausgabe-Override ``limit=all`` ODER ``all``.

    ``limit=all`` (case-insensitive, getrimmt) ist der self-documenting
    Escape-Hatch; ``?all=1``/``?all=true``/``?all=yes`` ist das aequivalente
    Flag. Beide erzwingen die Vollausgabe (limit ``None``) AUCH auf den gebundenen
    Kanaelen (GPT-Actions), der Override schlaegt also die Kanal-Erkennung.
    """
    limit_raw = qp.get("limit")
    if limit_raw is not None and limit_raw.strip().lower() == "all":
        return True
    all_raw = qp.get("all")
    return all_raw is not None and all_raw.strip().lower() in _TRUTHY_VALUES


def parse_page_params(request, *, default_limit: int = DEFAULT_LIMIT) -> PageParams:
    """Parst limit/offset/all (und page) aus ``request.query_params`` (ohne Depends).

    Gegenstueck zu ``page_params`` fuer Routen/Helper, in denen kein FastAPI-
    ``Depends`` greift (z.B. der geteilte OSM-Helper und die Store-Routen, die die
    Query selbst lesen). ``offset`` >= 0, ``page`` >= 1; nicht-numerisch/zu klein
    -> 400 invalid_request.

    KANAL-ABHAENGIGER Default (quick-260706-g9q, behebt den Breaking Change aus
    260706-chc). Aufloesungs-Reihenfolge fuer ``limit`` (Escape-Hatch zuerst):

    1. Vollausgabe-Override: ``limit=all`` ODER ``?all=1`` -> ``limit = None``
       (unbounded), kanalunabhaengig, schlaegt auch die GPT-Erkennung.
    2. Explizites numerisches ``limit``: ``>= 1``, ueber ``min(limit, MAX_LIMIT)``
       gedeckelt (gedeckelte Seite statt Fehler, Best-Practice #8). Der MCP-Client
       fuellt sein Default-limit selbst als expliziten Query-Parameter und faellt
       daher genau hierher (kein MCP-Raten im REST-Layer noetig).
    3. Kein ``limit``: kanal-abhaengiger Default -> ``is_gpt_action(request.headers)``
       True (GPT-Actions ueber OpenAI-Header/UA) -> ``limit = default_limit``
       (serverseitig erzwungenes Bound gegen das ~100-KB-GPT-Limit); False
       (direktes REST) -> ``limit = None`` (Vollausgabe, kein Breaking Change fuer
       Bestands-Bulk-Nutzer).

    ``sort``/``order`` werden fuer diese Datenart-Listen BEWUSST nicht angeboten:
    die zugrunde liegenden Listen tragen keine zugesicherte, stabile serverseitige
    Sortier-Ordnung, daher waere ein ``sort``-Versprechen unehrlich. Sie bleiben
    fix ``None`` / ``"asc"``, sodass ``paginate_envelope`` rein ueber offset/limit
    schneidet.
    """
    qp = request.query_params
    offset = _parse_int_param(qp.get("offset"), name="offset", minimum=0, default=0)
    page = _parse_int_param(qp.get("page"), name="page", minimum=1, default=1)

    limit: int | None
    if _is_full_output_override(qp):
        # 1. Vollausgabe-Override (kanalunabhaengig).
        limit = None
    elif qp.get("limit") is not None:
        # 2. Explizites numerisches limit (Bestandsverhalten inkl. MAX_LIMIT-Cap).
        limit = _parse_int_param(
            qp.get("limit"), name="limit", minimum=1, default=default_limit
        )
        limit = min(limit, MAX_LIMIT)
    else:
        # 3. Kein limit -> kanal-abhaengiger Default (GPT gebunden, REST voll).
        headers = getattr(request, "headers", {})
        limit = default_limit if is_gpt_action(headers) else None

    return PageParams(page=page, limit=limit, offset=offset, sort=None, order="asc")


def paginate_envelope(
    data: dict,
    meta: dict,
    p: PageParams,
    *,
    list_key: str,
    delivered_count_field: str | None = None,
) -> None:
    """Begrenzt eine Envelope-Liste EHRLICH und weist den Ausschnitt in meta aus.

    Schneidet ``data["payload"][list_key]`` auf die Seite ``[offset:offset+limit]``
    (Offset-Overflow -> leere Liste, KEIN Fehler, Best-Practice #8) und setzt
    ``meta["pagination"]`` = total/returned/limit/offset/truncated (keine stille
    Kappung, CLAUDE.md "No silent caps"). Item-Werte werden NICHT umgeschrieben, nur
    die Listenlaenge aendert sich (T-chc: nur Ausschnitt/Weglassen).

    Bei Vollausgabe (``p.limit is None``: direktes REST bzw. ``limit=all``) wird nur
    ab ``offset`` geschnitten (kein oberes Limit); ``meta.pagination`` weist dann
    ``limit=null``, ``returned==total`` und ``truncated=false`` aus (transparent auf
    allen Kanaelen).

    ``delivered_count_field`` (nur PoiPayload-Fall): ist es gesetzt, wird
    ``payload[delivered_count_field]`` auf die ausgelieferte Seitenlaenge gesetzt
    (die PoiPayload-Semantik: ``count`` = ausgelieferte Items) und, falls ein
    ``truncated``-Feld existiert, auf ``(total > returned) or bisheriger Wert``
    aktualisiert; ``total_available`` bleibt unangetastet (echter Gesamtbestand).
    Ist ``delivered_count_field`` ``None`` (energy/charging/events), bleiben die
    aggregierten Kennzahlen (count/by_type/total_power_kw) UNBERUEHRT: der Payload
    beschreibt weiter den vollen Snapshot, ``meta.pagination`` die ausgelieferte
    Seite (Auflage 2, ehrliche Trennung Aggregat vs. Seite).

    Defensiv: fehlt ``payload`` oder ``list_key`` oder ist kein ``list`` -> no-op.
    """
    payload = data.get("payload")
    if not isinstance(payload, dict):
        return
    items = payload.get(list_key)
    if not isinstance(items, list):
        return

    total = len(items)
    # limit=None: Vollausgabe (REST-Default / limit=all), nur ab offset.
    page = (
        items[p.offset :] if p.limit is None else items[p.offset : p.offset + p.limit]
    )
    payload[list_key] = page
    returned = len(page)

    meta["pagination"] = {
        "total": total,
        "returned": returned,
        "limit": p.limit,
        "offset": p.offset,
        "truncated": p.offset + returned < total,
    }

    if delivered_count_field is not None:
        payload[delivered_count_field] = returned
        if "truncated" in payload:
            payload["truncated"] = (total > returned) or bool(payload.get("truncated"))
