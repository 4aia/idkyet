"""Gemeinsame Feld-Normalisierer für Adapter (Konsistenz-Audit 2026-07-25).

Quellen liefern dieselben Konzepte in unterschiedlicher Form: PLZ mal als
integer (führende Null verloren), Adressteile mal als Leerstring, Hausnummern
mal im Straßennamen. Damit gleiche Felder über ALLE Endpunkte gleich aussehen,
liegen die Regeln hier zentral statt je Adapter kopiert:

- ``clean_text``: getrimmter, nicht leerer String, sonst ``None`` (nie ``""``).
- ``post_code``: immer fünfstelliger String, führende Null bleibt (01067).
- ``split_house_number``: trennt eine im Straßennamen mitgelieferte Hausnummer ab.

Alle Funktionen sind rein (kein I/O, kein Logging) und tolerant gegenüber
kaputtem Upstream: unbrauchbare Werte werden ``None``, nie geraten.
"""

from __future__ import annotations

import re

# Hausnummer am Ende eines Strassennamens: 1-4 Ziffern, optional ein
# angehaengter Buchstabe, optional ein zweiter Block ueber "-" oder "/"
# ("14", "23-29", "5 a", "28/30"). Bewusst eng gehalten, damit aus einem
# Strassennamen keine Hausnummer erfunden wird.
_HOUSE_NO_RE = re.compile(
    r"^(?P<street>.+?)[\s,]+(?P<num>\d{1,4}\s*[a-zA-Z]?(?:\s*[-/]\s*\d{1,4}\s*[a-zA-Z]?)?)$"
)


def clean_text(value: object) -> str | None:
    """Gibt einen getrimmten, nicht leeren String zurück, sonst None (rein).

    Quellen liefern Adressteile gelegentlich als Leerstring oder als reines
    Leerzeichen (z. B. Tankerkönig ``houseNumber: " "``, Köln-Events
    ``hausnummer: ""``); beides ist keine Angabe -> None. Nicht-Strings
    (Zahlen, ``None``, bool) sind kein Text -> None.
    """
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def post_code(value: object) -> str | None:
    """Normalisiert eine deutsche PLZ auf fünf Stellen als String (rein).

    Manche Quellen liefern die PLZ als integer (Tankerkönig ``postCode: 10407``);
    PLZ mit führender Null (01067 Dresden) kämen so als 1067 an. Deshalb immer
    String mit ``zfill(5)``. ``bool`` ist keine PLZ (bool < int), 0/leer -> None.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value).zfill(5) if value > 0 else None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped.zfill(5) if stripped else None
    return None


def _compact_house_number(raw: str) -> str:
    """Entfernt Leerraum innerhalb der Hausnummer (rein): "5 a" -> "5a"."""
    return re.sub(r"\s+", "", raw)


def split_house_number(street: str | None) -> tuple[str | None, str | None]:
    """Trennt eine im Strassennamen mitgelieferte Hausnummer ab (rein).

    Nicht jede Quelle fuellt ein eigenes Hausnummer-Feld: teils steht die Nummer
    im Strassennamen ("Rödingsmarkt 14", "Wendenstraße 23-29"), teils gibt es
    schlicht keine ("Theodor-Heuss-Platz"). Nur der erste Fall wird aufgetrennt.

    Konservativ: Der verbleibende Strassenname muss mindestens drei Zeichen und
    zwei Buchstaben haben, sonst wird NICHT getrennt (z. B. "B 75", "A 24"
    bleiben unveraendert). Passt nichts, kommt der Name unveraendert zurueck und
    die Hausnummer bleibt None - eine fehlende Nummer wird nie erfunden.
    """
    if not street:
        return street, None
    m = _HOUSE_NO_RE.match(street)
    if m is None:
        return street, None
    rest = m.group("street").strip(" ,")
    if len(rest) < 3 or sum(ch.isalpha() for ch in rest) < 2:
        return street, None
    return rest, _compact_house_number(m.group("num"))
