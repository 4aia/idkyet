"""Lokaler GeoIP/ASN-Lookup gegen DB-IP-Lite-mmdb-Dateien (Admin-Traffic-Tab).

Löst zu einer Client-IP das Herkunftsland (ISO-Code) und den Besitzer (ASN-
Organisation) auf, ausschließlich LOKAL: die mmdb-Dateien liegen auf dem Server
(``scripts/update_geoip.py`` lädt sie), keine Besucher-IP verlässt den Prozess.

Graceful Degradation: fehlt oder bricht eine Datenbank, bleibt der Reader ``None``
und ``lookup`` liefert None-Felder (die UI zeigt dann "-"), nie eine Exception.

Private-, Loopback-, Link-Local- sowie Tailnet-CGNAT-IPs (100.64.0.0/10) und nicht
parsebare Idents ("mcp"/"gpt") gelten als intern und werden NIE gegen die
Datenbanken aufgelöst.

Hinweis: die Reader werden beim ersten Lookup einmalig geöffnet und modulweit
gehalten (bewusst simpel). Nach einem DB-Update per Skript lädt der Prozess die
neue Datei erst nach einem Neustart.
"""

from __future__ import annotations

import functools
import ipaddress
import os

import maxminddb
import structlog

from infranode.config import get_settings

log = structlog.get_logger()

_COUNTRY_DB = "dbip-country-lite.mmdb"
_ASN_DB = "dbip-asn-lite.mmdb"

# Tailnet-CGNAT (100.64.0.0/10, RFC 6598): Tailscale nutzt diesen Bereich für
# interne Knoten. Nicht öffentlich routbar, aber (je nach Python-Version) NICHT
# in ``is_private`` enthalten -> explizit als intern behandeln.
_CGNAT = ipaddress.ip_network("100.64.0.0/10")

# Modul-Level-Reader-Cache: db-Dateiname -> geoeffneter Reader oder None (fehlt/
# kaputt). Membership zeigt an, dass ein Öffnen bereits versucht wurde.
_reader_cache: dict[str, maxminddb.Reader | None] = {}


def _open_reader(db_name: str) -> maxminddb.Reader | None:
    """Öffnet einen mmdb-Reader lazy und cached ihn modulweit (None bei Fehler)."""
    if db_name in _reader_cache:
        return _reader_cache[db_name]
    reader = None
    path = os.path.join(get_settings().geoip_dir, db_name)
    try:
        reader = maxminddb.open_database(path)
    except Exception as exc:
        log.debug("geoip_open_failed", db=db_name, error=str(exc))
    _reader_cache[db_name] = reader
    return reader


def _country_reader():
    """Reader der DB-IP-Lite-Country-Datenbank (None, wenn nicht verfügbar)."""
    return _open_reader(_COUNTRY_DB)


def _asn_reader():
    """Reader der DB-IP-Lite-ASN-Datenbank (None, wenn nicht verfügbar)."""
    return _open_reader(_ASN_DB)


def _is_internal(ip: str) -> bool:
    """True für nicht öffentlich routbare oder nicht parsebare Idents."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        # Nicht parsebar (z.B. "mcp"/"gpt") -> als intern behandeln.
        return True
    return addr.is_private or addr.is_loopback or addr.is_link_local or addr in _CGNAT


@functools.lru_cache(maxsize=4096)
def lookup(ip: str) -> dict:
    """Löst eine IP lokal zu ``{internal, country, asn, org}`` auf.

    ``country`` = ISO-Ländercode (z.B. "DE") oder None; ``asn`` = AS-Nummer oder
    None; ``org`` = AS-Organisation oder None. Interne IPs (privat/Loopback/CGNAT)
    und nicht parsebare Idents liefern ``internal=True`` ohne DB-Zugriff. Fehlende
    oder kaputte Datenbanken liefern None-Felder (graceful, kein Raise). Per-IP
    über ``functools.lru_cache`` gecached (in Tests via ``lookup.cache_clear()``
    zurücksetzen).
    """
    result = {"internal": False, "country": None, "asn": None, "org": None}
    if _is_internal(ip):
        result["internal"] = True
        return result

    country_reader = _country_reader()
    if country_reader is not None:
        try:
            record = country_reader.get(ip)
            if isinstance(record, dict):
                country = record.get("country")
                if isinstance(country, dict):
                    result["country"] = country.get("iso_code")
        except Exception as exc:
            log.debug("geoip_country_lookup_failed", error=str(exc))

    asn_reader = _asn_reader()
    if asn_reader is not None:
        try:
            record = asn_reader.get(ip)
            if isinstance(record, dict):
                result["asn"] = record.get("autonomous_system_number")
                result["org"] = record.get("autonomous_system_organization")
        except Exception as exc:
            log.debug("geoip_asn_lookup_failed", error=str(exc))

    return result
