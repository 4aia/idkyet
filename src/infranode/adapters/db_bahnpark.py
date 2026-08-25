"""DB-BahnPark-Adapter ``fetch_db_bahnpark`` (Phase 25, PARK-05, Tier A).

Bundesweiter Katalog bahnhofsnaher Parkeinrichtungen (~309 Häuser) aus dem DB API
Marketplace, Produkt "Parking Information Service (DB BahnPark)". Auth-Muster wie
``adapters/db_timetables`` / ``db_fasta``: Client-Id/Api-Key gehen NUR in die
Request-Header (DB-Client-Id / DB-Api-Key), nie in URL/Log.

Wichtig (Subscription "Testzugang", live verifiziert 2026-07-20):
- Der Endpunkt ist ``/parking-facilities`` (nicht ``/spaces``); die Anlagen stehen
  unter ``_embedded``. EIN Aufruf liefert alle Einrichtungen bundesweit.
- ``/parking-facilities`` liefert die STATISCHE Kapazität (``capacity[].total`` je
  ``type``), Adresse/Stadt und Koordinaten. Eine Live-Belegung gibt es nur je
  Einrichtung über ``/parking-facilities/{id}/capacities`` UND dort nur als grobe
  Kategorie (``free.category`` z.B. "MORE_THAN_FIFTY"), NICHT als exakte Zahl. Bei
  einem Kontingent von 1.000 Transaktionen/Monat (Testzugang) ist ein
  flächendeckendes Live-Polling nicht tragbar; DB BahnPark wird daher als
  STATISCHER Katalog geführt (``free=None``), analog München (DATA-40).

Dieser Adapter ist bewusst DÜNN: er holt den Feed und gibt die rohe
``_embedded``-Liste zurück. Das Parsen auf das einheitliche facility-Schema und die
Stadt->slug-Gruppierung sind rein und testbar in ``parking.db_bahnpark_store``. Der
tägliche Ingest (``ingest.db_bahnpark``) schreibt daraus den Katalog-Snapshot ins
Daten-Volume; der Request-Pfad liest NUR den Snapshot (kein Upstream-Call).

``resp.raise_for_status()`` ist Pflicht (5xx -> ``httpx.HTTPError``).

Sicherheit:
- T-25-19 (SSRF): Host + Produkt-Pfad in ``_URL`` hartkodiert; kein User-Input.
- T-25-20/T-08-CRED: db_client_id/db_api_key NUR im Header (SecretStr, .env
  out-of-repo), nie in URL/Cache-Key/Log.
- T-25-21 (DoS): raise_for_status + Fassade-Timeout begrenzen den Body.
"""

from __future__ import annotations

import httpx

# Host + Produkt-Pfad hartkodiert (SSRF, T-25-19): DB-API-Marketplace-Gateway,
# Produkt "Parking Information Service (DB BahnPark)", Endpunkt getParkingFacilities.
_URL = (
    "https://apis.deutschebahn.com/db-api-marketplace/apis"
    "/parking-information/db-bahnpark/v2/parking-facilities"
)


async def fetch_db_bahnpark(
    http: httpx.AsyncClient,
    *,
    client_id: str,
    api_key: str,
) -> list[dict]:
    """Holt den DB-BahnPark-Vollbestand und liefert die rohe ``_embedded``-Liste.

    Sendet die DB-API-Marketplace-Auth-Header (DB-Client-Id / DB-Api-Key). Rückgabe
    ist die unveränderte ``_embedded``-Liste (je Einrichtung u.a. ``id``, ``name``,
    ``address``, ``capacity``, ``station``); Transformation in ``db_bahnpark_store``.
    ``raise_for_status`` ist Pflicht (5xx -> Fassade STALE-ON-ERROR).
    """
    headers = {
        "DB-Client-Id": client_id,
        "DB-Api-Key": api_key,
        "Accept": "application/json",
    }
    resp = await http.get(_URL, headers=headers)
    resp.raise_for_status()
    body = resp.json()
    embedded = body.get("_embedded", []) if isinstance(body, dict) else []
    return embedded if isinstance(embedded, list) else []
