"""Reiner Mapper map_council_paper + per-Stadt-Lizenz-Map (council-papers, OParl).

Bildet ein vom Adapter (``adapters.oparl.fetch_papers``) geliefertes rohes
OParl-1.x-"Paper"-dict (Vorlage, Antrag, Beschluss eines kommunalen
Ratsinformationssystems) auf ein schlankes Store-row-dict ab. KEIN I/O, kein
Logging, kein Wall-Clock: der ``ingested_at``-Zeitanker wird injiziert.

``main_file_url`` wird NUR als Link durchgereicht (``mainFile.accessUrl`` bzw.
``mainFile.downloadUrl``); das PDF selbst wird NIE heruntergeladen/gespiegelt.

Anders als ``public-tenders`` (eine bundesweite CC0-Quelle) hat jede der acht
lizenzgeklärten Städte ihre EIGENE Lizenz. Deshalb liegt die per-Stadt-Lizenz in
``COUNCIL_CITY_LICENSE`` (Single Source of Truth für die Route-Attribution). Der
aggregierte Quellen-Eintrag in ``registry.source_specs`` (name="council") trägt
davon unabhängig eine übergreifende Beschreibung für die /sources-Route.
"""

from __future__ import annotations

# Lizenz-URLs VERBATIM aus den bestehenden Mappern (Lizenz-Drift-Konsistenz):
# DL-DE/Zero 2.0 wie pegelonline, DL-DE/BY 2.0 wie uba, CC BY 4.0 wie eea_bathing.
_DL_DE_ZERO_URL = "https://www.govdata.de/dl-de/zero-2-0"
_DL_DE_BY_URL = "https://www.govdata.de/dl-de/by-2-0"
_CC_BY_4_0_URL = "https://creativecommons.org/licenses/by/4.0/"


# Per-Stadt-Lizenz (Single Source of Truth für Route-Attribution + coverage).
# Dresden/Köln/Düsseldorf/Magdeburg = DL-DE/Zero 2.0, Münster/Freiburg =
# DL-DE/BY 2.0 (Namensnennung), Leipzig/Osnabrück = CC BY 4.0. modified=False: reine
# Durchreichung der OParl-Objekte (keine inhaltliche Bearbeitung). ``source`` =
# das OParl-System (Beleg der Herkunft). Attribution mit echten Umlauten (Prosa).
COUNCIL_CITY_LICENSE: dict[str, dict] = {
    "dresden": {
        "license_id": "dl_de_zero_2_0",
        "license_url": _DL_DE_ZERO_URL,
        "source": "https://oparl.dresden.de/system",
        "attribution": "Landeshauptstadt Dresden",
        "modified": False,
    },
    "koeln": {
        "license_id": "dl_de_zero_2_0",
        "license_url": _DL_DE_ZERO_URL,
        "source": "https://buergerinfo.stadt-koeln.de/oparl/system",
        "attribution": "Stadt Köln",
        "modified": False,
    },
    "duesseldorf": {
        "license_id": "dl_de_zero_2_0",
        "license_url": _DL_DE_ZERO_URL,
        "source": "https://ris-oparl.itk-rheinland.de/Oparl/system",
        "attribution": "Landeshauptstadt Düsseldorf",
        "modified": False,
    },
    "muenster": {
        "license_id": "dl_de_by_2_0",
        "license_url": _DL_DE_BY_URL,
        "source": "https://oparl.stadt-muenster.de/system",
        "attribution": "Stadt Münster",
        "modified": False,
    },
    "leipzig": {
        "license_id": "cc_by_4_0",
        "license_url": _CC_BY_4_0_URL,
        "source": (
            "https://ratsinformation.leipzig.de/allris_leipzig_public/oparl/system"
        ),
        "attribution": "Stadt Leipzig",
        "modified": False,
    },
    # Nord-Ergaenzung 2026-07-17: Lizenz je OParl-System-Objekt verifiziert.
    "magdeburg": {
        "license_id": "dl_de_zero_2_0",
        "license_url": _DL_DE_ZERO_URL,
        "source": "https://ratsinfo.magdeburg.de/oparl/system",
        "attribution": "Landeshauptstadt Magdeburg",
        "modified": False,
    },
    "osnabrueck": {
        "license_id": "cc_by_4_0",
        "license_url": _CC_BY_4_0_URL,
        "source": "https://www.osnabrueck.sitzung-online.de/oparl/system",
        "attribution": "Stadt Osnabrück",
        "modified": False,
    },
    # Freiburg 2026-08-01: Lizenz per Mail vom Ratsbüro der Stadt Freiburg
    # bestätigt (28.07.2026), das OParl-System-Objekt selbst nennt keine Lizenz.
    "freiburg-im-breisgau": {
        "license_id": "dl_de_by_2_0",
        "license_url": _DL_DE_BY_URL,
        "source": "https://ris.freiburg.de/oparl/system",
        "attribution": "Stadt Freiburg im Breisgau",
        "modified": False,
    },
}

# Single Source of Truth der abgedeckten Städte (Route-Guard + coverage). Genau
# die acht lizenzgeklärten Städte.
COVERED_COUNCIL_CITIES: frozenset[str] = frozenset(COUNCIL_CITY_LICENSE)


def _text(value: object) -> str | None:
    """Getrimmter String oder None (defensiv, kein KeyError bei fehlenden Feldern)."""
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _main_file_url(paper: dict) -> str | None:
    """Liest den Link zur Hauptdatei (mainFile.accessUrl || downloadUrl).

    NUR der Link (kein Download, PDFs werden NIE gespiegelt). Ein nicht-dict
    ``mainFile`` -> None (defensiv, kein Crash).
    """
    main_file = paper.get("mainFile")
    if not isinstance(main_file, dict):
        return None
    return _text(main_file.get("accessUrl")) or _text(main_file.get("downloadUrl"))


def map_council_paper(paper: dict, *, city_slug: str, ingested_at: str) -> dict:
    """Bildet ein rohes OParl-Paper-dict auf ein council_papers-Store-row ab.

    Rein (kein I/O), defensiv (None-Fallbacks je Feld). ``oparl_id`` = ``paper.id``
    (OParl-Objekt-ID, je Stadt eindeutig), ``name`` = ``paper.name`` bzw. ``.title``,
    ``reference`` = ``paper.reference``, ``date`` = ``paper.date``, ``paper_type`` =
    ``paper.paperType``, ``main_file_url`` = ``mainFile.accessUrl||downloadUrl``
    (nur Link), ``web`` = ``paper.web``, ``created`` = ``paper.created``,
    ``modified`` = ``paper.modified``. ``city_slug`` + ``ingested_at`` injiziert.
    """
    return {
        "city_slug": city_slug,
        "oparl_id": _text(paper.get("id")),
        "name": _text(paper.get("name")) or _text(paper.get("title")),
        "reference": _text(paper.get("reference")),
        "date": _text(paper.get("date")),
        "paper_type": _text(paper.get("paperType")),
        "main_file_url": _main_file_url(paper),
        "web": _text(paper.get("web")),
        "created": _text(paper.get("created")),
        "modified": _text(paper.get("modified")),
        "ingested_at": ingested_at,
    }
