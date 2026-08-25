// Zentrale Marketing-Kennzahlen für Landing-Seiten (DE + EN), damit Zahlen
// nicht je Seite auseinanderdriften (Audit 2026-08-13: die Stat-Zeile sagte
// noch "78 Datenarten" und "35+ Quellen", Titel und Fließtext derselben Seite
// "82"). Die Endpunktzahl kommt weiterhin zur Build-Zeit aus der
// endpoints-Collection (siehe scripts/check-endpoint-count.mjs).
//
// Pflege: Werte gegen die Live-API prüfen, /api/v1/sources (meta.total,
// Stand 2026-08-13: 98 registriert, davon 89 aktiv) und die Datenartenzahl
// des MCP-Katalogs (data_types_total). Floor-Werte ("95+") bewusst so
// gewählt, dass sie beim Wachstum wahr bleiben.
export const SITE_STATS = {
  cities: 84,
  dataTypes: 82,
  dataStreams: { de: "5.800+", en: "5,800+" },
  sources: { de: "95+", en: "95+" },
} as const;
