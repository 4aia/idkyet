"""Stadt-Register-Library: Großstädte + Lookup mit 404-Pfad (CORE-03/CORE-04).

Re-exportiert das ``CityRegistryEntry``-Modell und die ``CITY_REGISTRY``-
Konstante und stellt den ``get_city``-Lookup bereit. Der Lookup ist tolerant:
er löst Umlaut-, Schreibweisen-, Exonym- und Kurzform-Eingaben deterministisch
auf den kanonischen Slug auf (München/münchen/MÜNCHEN/munich/munchen ->
``muenchen``), damit auch fremde MCP-/API-Clients ohne unsere Prompt-Regeln
nicht an der ASCII-Slug-Schreibweise scheitern. Ein wirklich unbekannter Slug
wirft ``NotFoundError`` (aus der bestehenden Phase-1-Fehler-Infrastruktur) mit
einem "Meintest du"-Vorschlag im Hint; der zentrale Handler mappt das auf den
einheitlichen 404-Envelope. Die Schicht-Kopplung registry -> api/errors ist eine
bewusste, dokumentierte MVP-Entscheidung (02-RESEARCH Pattern 4 Variante a /
Open Question 2).
"""

from __future__ import annotations

import difflib
import unicodedata

from infranode.api.errors import NotFoundError
from infranode.registry.catalog import CITY_DATA_CATALOG
from infranode.registry.cities import _BY_SLUG, CITY_REGISTRY
from infranode.registry.models import CityRegistryEntry

__all__ = [
    "CITY_REGISTRY",
    "CityRegistryEntry",
    "get_city",
    "list_cities",
    "resolve_city_slug",
]

# Bekannte per-Stadt Sub-Ressourcen (Datenart-Keys aus dem Katalog + die Meta-
# Discovery-Ressource "overview"). Dient dem DX-Hinweis: ruft jemand
# /cities/<datenart> statt /cities/<stadt>/<datenart> ab, ist der "Slug" in
# Wahrheit eine Datenart, keine Stadt -> gezielter Korrektur-Hinweis.
_CITY_SUBRESOURCES: frozenset[str] = frozenset(
    {dt.key for dt in CITY_DATA_CATALOG} | {"overview"}
)

# Umlaut-Expansion (ä->ae ...) für die kanonische Slug-Schreibweise; ß wird
# bereits von str.casefold() zu "ss" (kein Eintrag nötig).
_EXPAND_UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue"})
# Bare-Vowel-Variante (ä->a ...) für die häufigste Fehleingabe: Umlaut ganz
# weggelassen (munchen, koln, dusseldorf, nurnberg).
_BARE_UMLAUT = str.maketrans({"ä": "a", "ö": "o", "ü": "u"})


def _slugify(text: str) -> str:
    """Reduziert Text auf Slug-Form: alphanumerische Zeichen, Nicht-Alnum-Runs
    werden zu genau einem Bindestrich, führende/abschließende Bindestriche weg."""
    out: list[str] = []
    prev_dash = False
    for ch in text:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")


def _prep(raw: str) -> str:
    """Gemeinsame Vorstufe: Unicode auf NFC komponieren (so wird ein zerlegtes
    'u' + kombinierender Umlaut, z.B. von macOS-Quellen, zum präkomponierten
    'ü'), trimmen und casefold. NFC ist Voraussetzung dafür, dass die Umlaut-
    Übersetzungstabellen greifen."""
    return unicodedata.normalize("NFC", raw).strip().casefold()


def _normalize(raw: str) -> str:
    """Kanonische Normalisierung: NFC + casefold + Umlaut-Expansion + Slugify.

    'München'/'münchen'/'MÜNCHEN' -> 'muenchen'; 'Frankfurt am Main' ->
    'frankfurt-am-main'; 'Halle (Saale)' -> 'halle-saale'.
    """
    return _slugify(_prep(raw).translate(_EXPAND_UMLAUT))


def _normalize_bare(raw: str) -> str:
    """Wie _normalize, aber Umlaute auf den bloßen Vokal (ä->a): fängt die
    'Umlaut weggelassen'-Eingabe generisch für jede Stadt ab (koln -> koeln)."""
    return _slugify(_prep(raw).translate(_BARE_UMLAUT))


def _build_index(transform) -> dict[str, str]:
    """Baut einen {normalisierte-Form -> kanonischer Slug}-Index aus Slug und
    ``name_de`` jeder Stadt (erste Zuordnung gewinnt, deterministisch)."""
    index: dict[str, str] = {}
    for city in CITY_REGISTRY:
        for source in (city.slug, city.name_de):
            index.setdefault(transform(source), city.slug)
    return index


_NORMALIZED_INDEX: dict[str, str] = _build_index(_normalize)
_BAREVOWEL_INDEX: dict[str, str] = _build_index(_normalize_bare)

# Echte Fremdnamen (Exonyme) + gängige Kurzformen, die sich NICHT aus der
# Normalisierung ergeben. Schlüssel werden normalisiert, Ziele gegen die
# Registry validiert (nicht existierende Aliase werden still verworfen).
_RAW_ALIASES: dict[str, str] = {
    # englische/fremdsprachige Exonyme
    "munich": "muenchen",
    "cologne": "koeln",
    "nuremberg": "nuernberg",
    "hanover": "hannover",
    "brunswick": "braunschweig",
    # gängige Kurzformen (Slug trägt einen Namenszusatz)
    "frankfurt": "frankfurt-am-main",
    "halle": "halle-saale",
    "freiburg": "freiburg-im-breisgau",
    "ludwigshafen": "ludwigshafen-am-rhein",
    "offenbach": "offenbach-am-main",
    "muelheim": "muelheim-an-der-ruhr",
}
_ALIASES: dict[str, str] = {
    _normalize(key): target
    for key, target in _RAW_ALIASES.items()
    if target in _BY_SLUG
}


def _did_you_mean(slug: str) -> str | None:
    """Bester Fuzzy-Treffer (cutoff 0.7) gegen normalisierte Slugs+Namen, auf
    den kanonischen Slug zurückgemappt; None wenn nichts nah genug ist."""
    norm = _normalize(slug)
    if not norm:
        return None
    match = difflib.get_close_matches(norm, list(_NORMALIZED_INDEX), n=1, cutoff=0.7)
    return _NORMALIZED_INDEX[match[0]] if match else None


def _unknown_city_hint(slug: str) -> str:
    """Baut den 404-Hint für einen unbekannten Stadt-Slug.

    Ist der Slug in Wahrheit eine Datenart (z.B. ``overview``, ``crime-stats``),
    hat der Aufrufer vermutlich den Stadt-Slug vergessen
    (``/cities/overview`` statt ``/cities/<stadt>/overview``); dann auf den
    per-Stadt-Pfad verweisen. Sonst, wenn ein ähnlicher Stadtname existiert,
    einen "Meintest du"-Vorschlag geben. Zuletzt der generische Listen-Hint.
    """
    base = "Nutze GET /api/v1/cities fuer alle unterstuetzten Staedte."
    key = slug.lower()
    if key in _CITY_SUBRESOURCES:
        return (
            f"'{slug}' ist eine Datenart, keine Stadt. Du hast vermutlich den "
            f"Stadt-Slug vergessen, z.B. GET /api/v1/cities/berlin/{key}. " + base
        )
    suggestion = _did_you_mean(slug)
    if suggestion is not None:
        return f"Meintest du '{suggestion}'? " + base
    return base


def resolve_city_slug(name: str) -> str | None:
    """Loest ``name`` DETERMINISTISCH auf den kanonischen Slug auf, sonst None.

    Der Nicht-Fuzzy-Kern von ``get_city``: exakte Slug-Schreibweise, dann
    Umlaut-/Schreibweisen-/Namens-Normalisierung, dann Bare-Vowel-Form, dann
    kuratierte Exonyme/Kurzformen. Bewusst OHNE difflib, damit ein Aufrufer
    zwischen "ist wirklich diese Stadt" und "sieht nur aehnlich aus"
    unterscheiden kann; ``api/path_hints`` haengt genau daran.
    """
    entry = _BY_SLUG.get(name.lower())
    if entry is not None:
        return entry.slug

    return (
        _NORMALIZED_INDEX.get(_normalize(name))
        or _ALIASES.get(_normalize(name))
        or _BAREVOWEL_INDEX.get(_normalize_bare(name))
    )


def get_city(slug: str) -> CityRegistryEntry:
    """Liefert den Stadt-Eintrag zum Slug oder wirft 404.

    Tolerant via ``resolve_city_slug``. Erst wenn nichts deterministisch
    aufloest, ein 404 mit "Meintest du"-Hint (Fuzzy wird NIE still umgeleitet).
    """
    target = resolve_city_slug(slug)
    if target is not None:
        return _BY_SLUG[target]

    raise NotFoundError(
        f"Unbekannte Stadt '{slug}'.",
        hint=_unknown_city_hint(slug),
    )


def list_cities() -> tuple[CityRegistryEntry, ...]:
    """Gibt alle registrierten Städte zurück (28 Kern + >100k-EW-Expansion)."""
    return CITY_REGISTRY
