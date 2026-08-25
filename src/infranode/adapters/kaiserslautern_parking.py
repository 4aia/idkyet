"""Keyloser Kaiserslautern-Parkleitsystem-Adapter ``fetch_kaiserslautern_parking``.

Direkter Zugang zur offenen Live-Parkbelegung der Stadtverwaltung Kaiserslautern
(Parkleitsystem, PLS). Live verifiziert 2026-07-19 ueber den CKAN-Datensatz
``parkhausbelegung`` auf ``opendata.kaiserslautern.de`` (Lizenz ``cc-zero`` = CC0):
die einzige Ressource ist eine XML-Datei unter
``https://www.kaiserslautern.de/live_tools/pls/pls.xml`` (keylos, HTTP 200).

Reales XML-Schema (live 2026-07-19, KEIN Namespace)::

    <Daten>
      <Zeitstempel>DD.MM.YYYY HH:MM:SS</Zeitstempel>
      <Parkhaus>
        <ID>2</ID><Name>PH Lutrinastrasse</Name>
        <Gesamt>142</Gesamt>     <!-- Kapazitaet -->
        <Aktuell>1</Aktuell>     <!-- aktuell FREIE Plaetze -->
        <Trend>0</Trend>
        <Status>Offen|Geschlossen</Status>
        <Oeffnungszeit1>...</Oeffnungszeit1><Oeffnungszeit2>...</Oeffnungszeit2>
      </Parkhaus>
      ...
    </Daten>

Rueckgabe ist das raw-dict, das ``map_kaiserslautern_parking`` erwartet: ``slug``
= "kaiserslautern", ``as_of`` (der Top-Level-``Zeitstempel`` in ISO 8601, oder
None) und ``facilities`` (je Parkhaus ein schlankes dict mit
facility_id/name/free/total/occupancy/state/trend/observed_at). Der Adapter baut
KEINEN ``CanonicalRecord`` und kennt KEIN Cache/Breaker (das liefert die
Resilienz-Fassade). ``resp.raise_for_status()`` ist Pflicht (5xx ->
STALE-ON-ERROR).

KEINE neue Dependency (Orchestrator-Decision 1, CLAUDE.md): das XML wird mit
stdlib ``xml.etree.ElementTree.iterparse`` geparst. Da dies ein LIVE-Request-Pfad
ist (untrusted), ist die XXE/DoS-Haertung aus ``adapters/mobidata_bw.py`` PFLICHT
(T-25-12):

1. Size-Cap ``_MAX_BYTES``: ein zu grosser Body wird gar nicht erst geparst.
2. Pre-Parse-Guard: ``<!DOCTYPE`` / ``<!ENTITY`` im Body -> ``ValueError`` BEVOR
   ``iterparse`` laeuft (verhindert XXE / Billion-Laughs, stdlib-only).
3. ``# noqa: S314, S405``: bewusst, weil die Mitigation der Pre-Parse-Guard +
   Size-Cap ist (keine stdlib-fremde XML-Dependency, Decision 1).

Sicherheit:
- T-25-13 (SSRF): Host + Ressourcen-Pfad sind in ``_BASE``/``_RESOURCE``
  hartkodiert; es fliesst kein User-Input in die URL.

Lizenz: CC0 (opendata.kaiserslautern.de, Datensatz ``parkhausbelegung``) = Tier A.
Siehe ``normalization/mappers/stadt_parking_b.map_kaiserslautern_parking``.
"""

from __future__ import annotations

import io
from datetime import datetime
from xml.etree.ElementTree import iterparse

import httpx

# Host + Ressourcen-Pfad hartkodiert (SSRF-Schutz, T-25-13).
_BASE = "https://www.kaiserslautern.de"
_RESOURCE = "/live_tools/pls/pls.xml"

# Size-Cap (T-25-12 DoS): der reale PLS-Feed ist wenige KB gross; 8 MiB deckt ihn
# mit grosser Reserve ab. Ein groesserer Body wird nicht geparst.
_MAX_BYTES = 8 * 1024 * 1024  # 8 MiB


def _localname(tag: str) -> str:
    """Gibt den lokalen Tag-Namen ohne XML-Namespace-Praefix zurueck."""
    return tag.rsplit("}", 1)[-1]


def _occupancy(free: int | None, capacity: int | None) -> float | None:
    """Auslastung in PROZENT (0..100) aus free/capacity (rein); unplausibel -> None.

    Wortgleich zu ``adapters/dortmund_parking._occupancy`` (Einheitlichkeit,
    Audit-Lehre 2026-06-29): eine Nachkommastelle, kein Prozent-Dialekt je Quelle.
    """
    if not isinstance(free, int) or not isinstance(capacity, int) or capacity <= 0:
        return None
    used = capacity - free
    if used < 0:
        return None
    return round(used / capacity * 100, 1)


def _to_int(value: str | None) -> int | None:
    """Parst einen XML-Textwert defensiv zu int (sonst None)."""
    if value is None:
        return None
    try:
        return int(value.strip())
    except (ValueError, AttributeError):
        return None


def _parse_de_timestamp(value: str | None) -> str | None:
    """Wandelt ``DD.MM.YYYY HH:MM:SS`` in einen ISO-8601-String (sonst None).

    Der Mapper (``stadt_parking_b._parse_as_of``) erwartet ISO; der reale Feed
    liefert deutsches Datumsformat -> hier einmalig konvertiert.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%d.%m.%Y %H:%M:%S").isoformat()
    except ValueError:
        return None


def _facility(fields: dict[str, str | None], *, observed_at: str | None) -> dict:
    """Bildet die Textfelder eines ``Parkhaus``-Elements auf ein facility-dict ab.

    Sentinel-Regeln (parkendd H8): ``Status`` geschlossen -> ``free = None``;
    ``free < 0`` -> None; ``free > total`` (unplausibel) -> None.
    ``Aktuell`` = aktuell freie Plaetze, ``Gesamt`` = Kapazitaet.
    """
    total = _to_int(fields.get("Gesamt"))
    free = _to_int(fields.get("Aktuell"))
    status = fields.get("Status")

    closed = isinstance(status, str) and status.strip().lower().startswith("geschl")
    if closed:
        free = None
    if isinstance(free, int) and free < 0:
        free = None
    if isinstance(free, int) and isinstance(total, int) and total > 0 and free > total:
        free = None

    return {
        "facility_id": fields.get("ID"),
        "name": fields.get("Name"),
        "free": free,
        "total": total,
        "occupancy": _occupancy(free, total),
        "state": status,
        "trend": _to_int(fields.get("Trend")),
        "observed_at": observed_at,
    }


def parse_kaiserslautern_parking(xml_bytes: bytes) -> dict:
    """Parst den Kaiserslautern-PLS-Body (rein, ohne Netz) zum raw-dict.

    Haertung (T-25-12, untrusted Live-Feed):
    - Size-Cap ``_MAX_BYTES``: zu grosser Body -> ``ValueError`` (kein Parse).
    - Pre-Parse-Guard: ``<!DOCTYPE`` / ``<!ENTITY`` -> ``ValueError`` VOR iterparse.

    Rueckgabe: ``{"slug": "kaiserslautern", "as_of": <iso|None>, "facilities": [...]}``.
    Ein leerer ``<Daten/>`` liefert ``facilities == []``.
    """
    # Size-Cap (T-25-12): zu grosse Bodies gar nicht erst parsen.
    if len(xml_bytes) > _MAX_BYTES:
        raise ValueError(
            f"Kaiserslautern-PLS-Body ueberschreitet _MAX_BYTES ({_MAX_BYTES})"
        )

    # Pre-Parse-Guard (T-25-12): DOCTYPE/ENTITY -> ABLEHNEN vor Parse (XXE/Billion-
    # Laughs). KEIN iterparse auf solchem Body (verhindert Entity-Expansion).
    if b"<!DOCTYPE" in xml_bytes or b"<!ENTITY" in xml_bytes:
        raise ValueError(
            "Kaiserslautern-PLS-Body enthaelt DOCTYPE/ENTITY (XXE/Billion-Laughs "
            "abgelehnt vor Parse, Pre-Parse-Guard T-25-12)"
        )

    as_of: str | None = None
    facilities: list[dict] = []
    bio = io.BytesIO(xml_bytes)

    # ist der Pre-Parse-Guard + Size-Cap oben (untrusted Live-Feed).
    for _event, elem in iterparse(bio):  # noqa: S314
        local = _localname(elem.tag)
        if local == "Zeitstempel" and as_of is None:
            # Top-Level-Zeitstempel (kommt im Dokument vor den Parkhaus-Eintraegen).
            as_of = _parse_de_timestamp(elem.text)
        elif local == "Parkhaus":
            fields = {
                _localname(child.tag): (child.text or "").strip() or None
                for child in elem
            }
            facilities.append(_facility(fields, observed_at=as_of))
            # Memory-konstant: das geparste Element sofort freigeben.
            elem.clear()

    return {"slug": "kaiserslautern", "as_of": as_of, "facilities": facilities}


async def fetch_kaiserslautern_parking(http: httpx.AsyncClient) -> dict:
    """Holt die Live-Parkbelegung Kaiserslautern und liefert das raw-dict.

    ``raise_for_status`` ist Pflicht (5xx -> Fassade STALE-ON-ERROR). Der reine
    Parse (inkl. XML-Haertung) liegt in ``parse_kaiserslautern_parking``.
    """
    url = f"{_BASE}{_RESOURCE}"
    resp = await http.get(url)
    resp.raise_for_status()
    return parse_kaiserslautern_parking(resp.content)
