// Drift-Check fuer die Endpunktzahl (Single Source of Truth).
//
// Die einzige Quelle der Endpunkte ist docs/openapi.yaml. Dieses Skript zaehlt
// die Operationen dort (genau wie docs-site/src/lib/openapi.ts: jede HTTP-
// Methode unter paths ist eine Operation, jede traegt eine operationId) und
// prueft, dass keine hartcodierte Zahl davon abweicht:
//
//   - README.md (deutsche Hauptfassung): die Zahl in der Ueberschrift
//     "## Daten (84 Städte, N Endpunkte)" muss dem Zaehlwert entsprechen.
//   - README.en.md (englische Fassung): dasselbe fuer die Ueberschrift
//     "## Data (84 cities, N endpoints)".
//   - docs-site/src/pages/index.astro (DE) und en/index.astro (EN): duerfen
//     KEINE feste Zahl vor "Endpunkte"/"endpoints" mehr enthalten, sondern
//     muessen den zur Build-Zeit berechneten Wert {endpointCount} verwenden.
//
// Aufruf: `npm run check:endpoint-count` (in docs-site/) oder
//         `node scripts/check-endpoint-count.mjs`.
// Exit-Code 1 bei jeder Abweichung, damit CI/Precommit rot wird.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { parse } from "yaml";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(HERE, "..", "..");
const SPEC_PATH = resolve(REPO, "docs", "openapi.yaml");
const README_PATH = resolve(REPO, "README.md");
const README_EN_PATH = resolve(REPO, "README.en.md");
const INDEX_DE = resolve(REPO, "docs-site", "src", "pages", "index.astro");
const INDEX_EN = resolve(REPO, "docs-site", "src", "pages", "en", "index.astro");

const HTTP_METHODS = ["get", "put", "post", "delete", "patch", "options", "head", "trace"];

// Zaehlt die Operationen in der Spec, identisch zur loadEndpoints-Logik.
function countOperations() {
  const spec = parse(readFileSync(SPEC_PATH, "utf-8"));
  const paths = spec?.paths ?? {};
  let count = 0;
  for (const pathItem of Object.values(paths)) {
    if (pathItem == null || typeof pathItem !== "object") continue;
    for (const method of HTTP_METHODS) {
      const op = pathItem[method];
      if (op != null && typeof op === "object") count += 1;
    }
  }
  return count;
}

const expected = countOperations();
const errors = [];

// READMEs (deutsch + englisch): die feste Zahl in der jeweiligen Ueberschrift
// muss stimmen. Beide werden gegen denselben Zaehlwert geprueft.
for (const [label, file, pattern, unit] of [
  ["README.md", README_PATH, /(\d+)\s+Endpunkte/, "Endpunkte"],
  ["README.en.md", README_EN_PATH, /(\d+)\s+endpoints/i, "endpoints"],
]) {
  const src = readFileSync(file, "utf-8");
  const match = src.match(pattern);
  if (!match) {
    errors.push(`${label}: keine "N ${unit}"-Angabe gefunden.`);
  } else if (Number(match[1]) !== expected) {
    errors.push(`${label}: ${match[1]} statt ${expected} (aus docs/openapi.yaml).`);
  }
}

// index.astro DE/EN: kein hartcodierter Zahlenwert, Wert muss dynamisch sein.
for (const [label, file] of [
  ["index.astro (DE)", INDEX_DE],
  ["en/index.astro (EN)", INDEX_EN],
]) {
  const src = readFileSync(file, "utf-8");
  const hard = src.match(/\d+\s+(?:Endpunkte|endpoints)/);
  if (hard) {
    errors.push(
      `${label}: hartcodierte Endpunktzahl "${hard[0]}" gefunden. ` +
        `Stattdessen {endpointCount} aus getCollection("endpoints") verwenden.`,
    );
  }
  if (!src.includes("endpointCount")) {
    errors.push(`${label}: verwendet endpointCount nicht (dynamischer Wert fehlt).`);
  }
}

if (errors.length > 0) {
  console.error(`Endpunktzahl-Drift erkannt (Quelle docs/openapi.yaml: ${expected}):`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
}

console.log(`OK: Endpunktzahl konsistent (${expected} Operationen aus docs/openapi.yaml).`);
