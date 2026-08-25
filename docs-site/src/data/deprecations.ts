// Single Source für die Abkündigungs-Banner auf den Endpunkt-Seiten
// (/api/<operationId> und /en/api/<operationId>). Ein Eintrag je betroffener
// Operation: welche Feldnamen abgekündigt sind und wie sie jetzt heißen.
//
// Warum hier und nicht in der OpenAPI-Beschreibung: die Spec sagt es im
// Fließtext, ein Banner sieht man auch beim Überfliegen. Beide Quellen müssen
// zusammenpassen, deshalb steht die Frist genau einmal in REMOVAL_DATE.
//
// Nach dem Entfernen der Felder: den betroffenen Eintrag hier löschen (dann
// verschwindet das Banner) und im Changelog einen "removed"-Eintrag ergänzen.

/** Frühestes Entfernungsdatum, 30 Tage nach der jüngsten Ankündigung vom 2026-08-01. */
export const REMOVAL_DATE = { de: "31. August 2026", en: "31 August 2026" };

export interface DeprecatedField {
  /** Alter Name, der weiterhin denselben Wert trägt. */
  old: string;
  /** Kanonischer Name, auf den umgestellt werden soll. */
  now: string;
}

/** operationId -> abgekündigte Felder dieser Operation. */
export const FIELD_DEPRECATIONS: Record<string, DeprecatedField[]> = {
  getCityCharging: [
    { old: "plz", now: "post_code" },
    { old: "ort", now: "place" },
  ],
  getCityEnergy: [
    { old: "plz", now: "post_code" },
    { old: "leistung_kw", now: "power_kw" },
    { old: "einheit_typ", now: "asset_type" },
  ],
  getCityStations: [
    { old: "zip", now: "post_code" },
    { old: "category", now: "station_category" },
  ],
  getCityHospitalsAtlas: [
    { old: "zip", now: "post_code" },
    { old: "city", now: "place" },
  ],
  getCityEvents: [
    { old: "strasse", now: "street" },
    { old: "hausnummer", now: "house_number" },
    { old: "plz", now: "post_code" },
    { old: "title", now: "name" },
  ],
  getCityRoadEvents: [
    // Köln (Stufe 1) + Stadtquellen München/Rostock/Dortmund/Sachsen/Hamburg
    // (Stufe 3); je Quelle tragen die Events nur die dort vorhandenen Felder.
    { old: "bezeichnung", now: "name" },
    { old: "beginn", now: "start" },
    { old: "ende", now: "end" },
    { old: "art", now: "event_type" },
    { old: "beschreibung", now: "description" },
    { old: "von", now: "start" },
    { old: "bis", now: "end" },
    { old: "strasse", now: "street" },
    { old: "strasse_hausnr", now: "street" },
    { old: "betroffene_bereiche", now: "affected_areas" },
    { old: "sparte", now: "sector" },
    { old: "einschraenkung", now: "restriction" },
    { old: "abschnitt_von", now: "section_from" },
    { old: "abschnitt_nach", now: "section_to" },
    { old: "baubeginn", now: "start" },
    { old: "bauende", now: "end" },
    { old: "typ", now: "closure_type" },
    { old: "grund", now: "reason" },
    { old: "strassenklasse", now: "road_class" },
    { old: "ortslage", now: "location" },
    { old: "umleitung_ueber", now: "diversion_via" },
    { old: "auftraggeber", now: "client" },
    { old: "zeitraum", now: "period" },
    { old: "stadtbezirk", now: "district" },
    { old: "titel", now: "name" },
    { old: "anlass", now: "reason" },
  ],
  getCityFuelPrices: [{ old: "dist_km", now: "distance_km" }],
  getCityTraffic: [
    { old: "isBlocked", now: "is_blocked" },
    { old: "startTimestamp", now: "start_timestamp" },
    { old: "delayTimeValue", now: "delay_minutes" },
    { old: "averageSpeed", now: "average_speed_kmh" },
    { old: "abnormalTrafficType", now: "abnormal_traffic_type" },
    { old: "extent", now: "bbox" },
  ],
  getCityStationDepartures: [{ old: "stop_id", now: "trip_stop_id" }],
  getCityStationArrivals: [{ old: "stop_id", now: "trip_stop_id" }],
  getStationDepartures: [{ old: "stop_id", now: "trip_stop_id" }],
  getStationArrivals: [{ old: "stop_id", now: "trip_stop_id" }],
  getCityFlood: [{ old: "stand", now: "as_of" }],
  getCityFireDanger: [{ old: "bundesland", now: "federal_state" }],
  getCityElection: [{ old: "granularity", now: "coverage_granularity" }],
  getCityTreeCadastre: [
    // Rohe WFS-Feldnamen je Stadt (Berlin/Hamburg/Kiel); je Stadt tragen die
    // Items nur die dort vorhandenen Felder.
    { old: "art_dtsch", now: "species" },
    { old: "art_deutsch", now: "species" },
    { old: "Baumart", now: "species" },
    { old: "art_bot", now: "species_botanical" },
    { old: "Baumart__bot._", now: "species_botanical" },
    { old: "gattung_deutsch", now: "genus" },
    { old: "pflanzjahr", now: "planting_year" },
    { old: "Kronendurchmesser__m_", now: "crown_diameter_m" },
  ],
  getCityHeritage: [
    // Rohe WFS-Feldnamen je Land (Berlin/Hamburg/Hessen); "info" und "link"
    // sind bereits englisch und bleiben unverändert.
    { old: "typ", now: "type" },
    { old: "bezeichnung", now: "name" },
    { old: "bautyp", now: "building_type" },
    { old: "baujahr", now: "build_year" },
    { old: "siteName", now: "site_name" },
    { old: "siteDesignation", now: "site_designation" },
    { old: "publicationSource", now: "publication_source" },
  ],
  getCityLandValues: [{ old: "stichtag", now: "reference_date" }],
  getCityTaxRates: [
    { old: "gewerbesteuer_hebesatz", now: "trade_tax_rate" },
    { old: "grundsteuer_a", now: "property_tax_a" },
    { old: "grundsteuer_b", now: "property_tax_b" },
    { old: "grundsteuer_c", now: "property_tax_c" },
    { old: "stichtag", now: "reference_date" },
  ],
  getCityBusinessRegistrations: [
    { old: "anmeldungen", now: "registrations" },
    { old: "abmeldungen", now: "deregistrations" },
    { old: "saldo", now: "balance" },
    { old: "jahr", now: "year" },
  ],
  getCityInsolvencies: [
    { old: "unternehmensinsolvenzen", now: "corporate_insolvencies" },
    { old: "uebrige_schuldner_insolvenzen", now: "other_debtor_insolvencies" },
    { old: "jahr", now: "year" },
  ],
};
