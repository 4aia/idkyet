"""Reiner Wegweiser-Mapper ``map_indicator_series`` (Bertelsmann Stiftung, CC0).

Bildet die Indikator-Zeitreihen aus dem SQLite-Reader
(``archive.wegweiser_db.read_series``) deterministisch auf einen
``CanonicalRecord`` mit ``IndicatorSeriesPayload`` ab. Rein: kein HTTP, kein
Logging, kein ``datetime.now()`` (``retrieved_at`` wird injiziert).

Quelle ist der Wegweiser Kommune der Bertelsmann Stiftung. Die
Nutzungsbedingungen sagen wörtlich: "Die Inhalte des Wegweiser Kommune werden
unentgeltlich von der Bertelsmann Stiftung zur Verfügung gestellt und stehen
unter der Datenlizenz CC0". CC0 verlangt KEINE Attribution; wir nennen die
Herkunft trotzdem, weil das Feld dem Nutzer sagt, woher die Zahl stammt, und
weil hinter den Berechnungen amtliche Statistiken stehen, deren Nennung fair
ist. ``modified=False``: die Werte sind unverändert, wir gruppieren sie nur.

``geo`` bleibt ``None`` (Gemeindeebene), ``observed_at`` bleibt ``None``: die
Jahre stehen je Indikator in der Zeitreihe, ein einzelner Beobachtungszeitpunkt
wäre für einen Bestand von 2006 bis 2040 irreführend.

## Themen-Registry

``TOPIC_TO_DATASET`` ordnet die Themen der Quelle unseren Datenarten zu. Der
Ingest zieht IMMER den ganzen Bestand, unabhängig von dieser Tabelle; eine
weitere Datenart ist damit genau ein Eintrag hier plus Route und Katalog, ohne
erneuten Ingest. ``dataset_indicators`` löst eine Datenart in die Liste der
Indikator-Schlüssel auf, die der Reader dann bindet.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from infranode.config import Settings
from infranode.normalization import (
    Attribution,
    CanonicalRecord,
    IndicatorSeriesPayload,
    LicenseId,
    LicenseTier,
    SourceId,
)

_CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"

# Wegweiser-Thema (wortgleich wie in der Quelle) -> InfraNode-Datenart.
# Mehrere Themen duerfen auf dieselbe Datenart zeigen; ein Indikator zaehlt dazu,
# sobald EINES seiner Themen passt (die Quelle haengt Indikatoren an mehrere).
#
# Der Schnitt folgt der Frage, die ein Nutzer stellt, nicht der Themen-Gliederung
# der Quelle: die 23 Quell-Themen sind teils sehr fein (fuenf Varianten von
# "Altersgruppen"). Gebuendelt wird deshalb nach Ist-Zustand (population-structure)
# gegen Veraenderung (population-trend) und nach Lebensbereich.
#
# Bewusst NICHT gemappt: "Wanderungen nach Ziel und Herkunft" (nur 33 Werte fuer
# 9 Staedte, zu duenn fuer eine eigene Datenart).
TOPIC_TO_DATASET: dict[str, str] = {
    "Nachhaltigkeit / SDGs": "sustainability",
    # Altersaufbau im Ist-Zustand, inkl. Prognosejahren bis 2040.
    "Bevölkerung nach Altersgruppen": "population-structure",
    "Anteile der Altersgruppen": "population-structure",
    "Anteil der Altersgruppen": "population-structure",
    "Bevölkerung nach Altersgruppen und Geschlecht": "population-structure",
    "Anteile der Altersgruppen nach Geschlecht": "population-structure",
    "Bevölkerung nach Generationen": "population-structure",
    "Demografie - Bevölkerungsstand": "population-structure",
    # Veraenderungsraten: wie sich der Altersaufbau bewegt.
    "Entwicklung der Altersgruppen": "population-trend",
    "Entwicklung der Altersgruppen seit 2011": "population-trend",
    "Entwicklung der Altersgruppen nach Geschlecht seit 2011": "population-trend",
    "Demografische Entwicklung": "population-trend",
    "Demografie - Bevölkerungsveränderung": "population-trend",
    # Kommunale Finanzen: Hebesaetze, Steuerkraft, Schulden, Investitionen.
    # Ergaenzt tax-rates (Regionalstatistik) um die HISTORIE, ersetzt es nicht.
    "Finanzen": "municipal-finance",
    # Arbeitsmarkt inkl. Pendlerverflechtung.
    "Beschäftigung / Arbeitsmarkt": "labour-market",
    "Pendler:innen": "labour-market",
    "Integration": "integration",
    "Kinderbetreuung": "childcare",
    # Bildungsstatistik. NICHT zu verwechseln mit der Datenart "education",
    # die OSM-Schulstandorte als POIs fuehrt; deshalb der eigene Name.
    "Schüler:innen und Abschlüsse": "education-stats",
    "Aus- und Weiterbildung": "education-stats",
    "Soziale Lage": "social-situation",
    "Pflege": "care",
}


def _db_path() -> Path:
    """Liest den SQLite-Pfad frisch aus der Env (tmp_path-Override greift)."""
    return Path(Settings().archive_dir) / "wegweiser.db"


def dataset_indicators(dataset: str) -> list[str]:
    """Liefert die Indikator-Schlüssel einer Datenart aus dem jüngsten Snapshot.

    Gelesen wird die ``topics``-Spalte der Indikator-Metadaten und über
    ``TOPIC_TO_DATASET`` auf die Datenart abgebildet. Ein Indikator zählt dazu,
    sobald EINES seiner Themen auf diese Datenart zeigt (die Quelle hängt
    Indikatoren an mehrere Themen).

    Graceful Degradation: fehlende DB-Datei oder fehlende Tabelle -> ``[]``, die
    Route meldet dann ``not_ingested`` statt eines 5xx.
    """
    topics = {topic for topic, name in TOPIC_TO_DATASET.items() if name == dataset}
    if not topics:
        return []

    path = _db_path()
    if not path.exists():
        return []

    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        try:
            rows = db.execute(
                "SELECT indicator, topics FROM wegweiser_indicators "
                "WHERE ingest_date = "
                "(SELECT MAX(ingest_date) FROM wegweiser_indicators)"
            ).fetchall()
        except sqlite3.OperationalError:
            return []
    finally:
        db.close()

    keys = []
    for indicator, raw in rows:
        try:
            entries = json.loads(raw) if raw else []
        except json.JSONDecodeError:
            continue
        if topics.intersection(entries):
            keys.append(indicator)
    return sorted(keys)


def map_indicator_series(
    slug: str,
    rows: list[dict],
    *,
    dataset: str,
    retrieved_at: datetime,
    ags: str | None = None,
    wikidata_qid: str | None = None,
) -> CanonicalRecord:
    """Bildet die Zeitreihen einer Stadt auf einen ``CanonicalRecord`` ab.

    ``rows`` ist die vom SQLite-Reader gelieferte Liste (``key``/``name``/
    ``unit``/``source``/``explanation``/``latest_year``/``latest_value``/
    ``series``). ``retrieved_at`` wird injiziert (kein ``datetime.now()`` im
    Mapper), damit das Ergebnis deterministisch bleibt. Die Join-Keys
    ``ags``/``wikidata_qid`` kommen aus dem Register.

    ``year_min``/``year_max`` werden über alle Reihen aufgespannt; sind gar keine
    Punkte da, bleiben beide ``None`` statt auf 0 zu fallen.
    """
    years = [point["year"] for row in rows for point in row.get("series") or []]

    return CanonicalRecord(
        city_slug=slug,
        geo=None,
        observed_at=None,
        retrieved_at=retrieved_at,
        source=SourceId.WEGWEISER,
        license_id=LicenseId.CC0,
        license_tier=LicenseTier.A,
        ags=ags,
        wikidata_qid=wikidata_qid,
        attribution=Attribution(
            text="Wegweiser Kommune, Bertelsmann Stiftung (CC0)",
            license_url=_CC0_URL,
            modified=False,
        ),
        payload=IndicatorSeriesPayload(
            dataset=dataset,
            indicator_count=len(rows),
            year_min=min(years) if years else None,
            year_max=max(years) if years else None,
            indicators=rows,
        ),
    )
