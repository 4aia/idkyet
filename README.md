Deutsch | [English](./README.en.md)

# Atlas

Ein MCP-Server für offene Daten deutscher Städte — Wetter, Luftqualität, ÖPNV,
Verkehr, Energie, Demografie und mehr, über eine Handvoll Tools statt über 25
verschiedene Behörden-APIs mit je eigenem Format.

## Warum

Deutsche Städte und Ämter veröffentlichen viel Open Data, aber jede Quelle hat
ihr eigenes Format, eigene Feldnamen und eigene Eigenheiten. Atlas normalisiert
rund 25 Upstream-Quellen (DWD, UBA, Deutsche Bahn, SMARD, BORIS,
Bundesnetzagentur, OpenStreetMap, GovData, ...) auf ein gemeinsames Schema und
macht sie für KI-Agenten über MCP nutzbar. Kein API-Key, kein Konto, keine 25
APIs lernen.

## Einstieg

Ein Aufruf reicht: `get_city_overview(slug)` liefert die Stammdaten einer
Stadt, den Katalog aller verfügbaren Datenarten (mit Abdeckungsstatus und dem
passenden Tool) und einen kleinen Live-Auszug (Wetter, Luft, Bahn-Abfahrten).
Von dort aus geht es entweder über ein paar benannte Tools weiter (`weather`,
`air_quality`, `pois`, `compare`, die Bahnhofstafeln) oder generisch über
`get_city_resource(slug, resource=<key>)` für jede weitere Datenart.

Stadtnamen werden tolerant aufgelöst: mit oder ohne Umlaut, jede
Schreibweise, gängige englische Exonyme (`munich`, `cologne`, ...). Ein
unbekannter Name liefert einen Vorschlag statt eines nackten Fehlers.

## Verbinden

```bash
claude mcp add --transport http atlas https://mcp.woof.systems/mcp
```

Jeder andere MCP-Client (Cursor, Windsurf, Claude Desktop, ein
ChatGPT-Connector) auf denselben Remote-Endpunkt:

```jsonc
{
  "mcpServers": {
    "atlas": { "url": "https://mcp.woof.systems/mcp" }
  }
}
```

Alle Tools sind read-only (`readOnlyHint`, `idempotentHint`), MCP-Clients
können sie also ohne Rückfrage freigeben. Details, das vollständige
Tool-Manifest mit Beispielausgaben und das Berechtigungsmodell stehen in
[docs/mcp-install.md](./docs/mcp-install.md). Das Registry-Manifest ist
[server.json](./server.json).

## Wie es funktioniert

Ein gemeinsamer HTTP-Client fragt die Upstream-Quellen ab, jede Antwort wird
auf ein kanonisches `{ data, meta }`-Schema gemappt, durchs Lizenz-Gate
geführt (Attribution je Datensatz) und in Redis gecacht (mit
Stale-on-Error-Fallback). Fällt eine Quelle aus, zeigt sich das in
`meta.source_status` — der Aufruf selbst schlägt dadurch nicht fehl.

Die REST-API dahinter ist ein internes Implementierungsdetail; der
MCP-Server ist die einzige öffentliche Schnittstelle.

Feldnamen sind über alle Datenarten hinweg snake_case und englisch, dasselbe
Konzept heißt immer gleich (`post_code`, `street`, `lat`, `lon`, `start`,
`end`, ...). Ein Wert, den die Quelle nicht liefert, ist `null`, nie ein
leerer String.

## Daten

84 Städte, rund 82 Datenarten:

- **Wetter & Umwelt** — Wetter, Wetterwarnungen, Luftqualität, Pollen/UV,
  Pegelstände, Hochwasser, Waldbrandgefahr
- **Mobilität** — ÖPNV-Echtzeitabfahrten, Bahnhofstafeln, Verkehr, Parken,
  Ladeinfrastruktur, Sharing, Spritpreise
- **Stadt & Menschen** — Demografie, Gesundheit, Bildung, Veranstaltungen,
  Ratsinformationen, Points of Interest
- **Wirtschaft** — Bodenrichtwerte, Gewerbesteuer, öffentliche Vergabe
- **Energie & Fahrzeuge** — Strompreis, Solar, Fernwärme, Kfz-Bestand

Quellen u.a.: Deutscher Wetterdienst, Umweltbundesamt, Deutsche Bahn, VBB,
SMARD, BORIS, Bundesnetzagentur, KBA, OpenStreetMap, GovData.

## Lokal laufen lassen

```bash
cp .env.example .env
docker compose -f deploy/docker-compose.yml up
curl http://localhost/api/v1/health
```

MCP-Server gegen die lokale API starten:

```bash
uv sync --group mcp
mcpApiBase=http://localhost/api/v1 uv run python -m infranode.mcp.server
```

Alle Einstellungen sind einfache camelCase-Variablen ohne Prefix (siehe
`.env.example`). Echte Secrets landen nie im Repo, versioniert ist nur
`.env.example`.

## Status

Der MCP-Server wird gerade von Python nach Go migriert; die REST-API bleibt
vorerst Python. Bis zum Cutover laufen beide nebeneinander, ohne dass sich am
öffentlichen MCP-Interface etwas ändert.

## Lizenz

Closed Source, alle Rechte vorbehalten (siehe [LICENSE](./LICENSE)). Die
durchgereichten Daten behalten die Lizenzen ihrer Upstream-Quellen (z.B. ODbL
für OpenStreetMap, Namensnennungspflicht für DWD) — jede Antwort trägt ihre
eigene `attribution`.
