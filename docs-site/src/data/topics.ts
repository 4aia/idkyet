// Single Source für die per-Datentyp-Landingpages (SEO-Maßnahme 1).
// Jede Datenachse (Wetter, Luftqualität, Strompreis, Bodenrichtwerte,
// ÖPNV-Echtzeit) bekommt eine keyword-optimierte Seite in DE und EN, gespeist
// aus diesem Array. Die dynamischen Routen src/pages/daten/[topic].astro und
// src/pages/en/data/[topic].astro generieren daraus die Seiten.
//
// coverageKey: Schlüssel in src/data/coverage.json#partial für die Stadt-Zahl.
// "all" = alle Städte (nationale/flächendeckende Quelle). endpointId verlinkt
// in die API-Referenz (/api/{endpointId}/ bzw. /en/api/{endpointId}/).

export interface TopicFaq {
  q: string;
  a: string;
}

export interface TopicLang {
  slug: string;
  metaTitle: string;
  h1: string;
  lead: string;
  dataDesc: string;
  sourceName: string;
  sourceUrl: string;
  license: string;
  licenseUrl: string;
  vars: string[];
  keywords: string[];
  coverageNote: string;
  faq: TopicFaq[];
  datasetName: string;
  datasetDesc: string;
}

export interface Topic {
  id: string;
  endpointId: string;
  examplePath: string; // Pfad nach /api/v1 ... mit Beispiel-Slug
  coverageKey: string; // "all" oder Key aus coverage.json#partial
  de: TopicLang;
  en: TopicLang;
}

export const topics: Topic[] = [
  {
    id: "fuel-prices",
    endpointId: "getCityFuelPrices",
    examplePath: "/api/v1/cities/koeln/fuel-prices",
    // Kein eigener Coverage-Key: die Route kennt keine Stadt-Allowlist, sie
    // rechnet für jede Register-Stadt über die Tankstellen im Suchradius. Die
    // frühere Liste mit 40 Städten stammte aus einem Live-Sweep, der von der
    // Quelle abgeschnitten wurde, und war damit zu klein (gegengeprüft am
    // 29.07.: mannheim und luebeck fehlten in der Liste, liefern aber ok).
    coverageKey: "all",
    de: {
      slug: "spritpreise-api",
      metaTitle: "Spritpreise-API Deutschland (MTS-K), keylos",
      h1: "Spritpreise-API für deutsche Städte (MTS-K)",
      lead: "Aktuelle Kraftstoffpreise je Stadt über eine kostenlose, keylose REST-API. Grundlage sind die Meldedaten der Markttransparenzstelle für Kraftstoffe, abgerufen über Tankerkönig und je Stadt zu Durchschnitts- und Bestpreisen verrechnet.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt Durchschnitts- und Minimalpreis für Super E5, Super E10 und Diesel über die aktuell geöffneten Tankstellen im Stadtumkreis, dazu die Zahl der berücksichtigten und der geöffneten Tankstellen, den Suchradius sowie die Einzelstationen mit Marke, Adresse, Entfernung und Öffnungsstatus.",
      sourceName: "Tankerkönig / Markttransparenzstelle für Kraftstoffe (MTS-K)",
      sourceUrl: "https://creativecommons.tankerkoenig.de/",
      license: "CC BY 4.0",
      licenseUrl: "https://creativecommons.org/licenses/by/4.0/",
      vars: ["Durchschnittspreis E5, E10, Diesel", "Bestpreis je Sorte", "Anzahl Tankstellen im Radius", "Anzahl geöffneter Tankstellen", "Suchradius in Kilometern", "Marke und Name je Tankstelle", "Entfernung zur Stadtmitte", "Öffnungsstatus"],
      keywords: ["Spritpreise API", "Tankstellen API Deutschland", "Benzinpreise API", "Dieselpreis API", "MTS-K Daten", "Kraftstoffpreise Open Data"],
      coverageNote: "Alle Städte im Register. Die Stadt-Kennzahlen sind berechnet, nicht gemeldet: sie entstehen aus den geöffneten Tankstellen im Suchradius um die Stadtkoordinate. Liegt dort gerade keine geöffnete Tankstelle, meldet die Antwort ehrlich, dass keine Daten vorliegen, statt einen Wert zu erfinden.",
      faq: [
        {
          q: "Wie aktuell sind die Preise?",
          a: "Die Preise werden bei der Anfrage abgerufen und nur sehr kurz zwischengespeichert. Jede Antwort trägt den Abrufzeitpunkt. Historische Preise halten wir bewusst nicht dauerhaft vor, das untersagen die Nutzungsbedingungen der Quelle.",
        },
        {
          q: "Warum weicht der Durchschnittspreis von einzelnen Tankstellen ab?",
          a: "Der Stadtwert ist ein berechneter Mittelwert über die geöffneten Tankstellen im Umkreis der Stadtkoordinate. Einzelne Stationen können deutlich darüber oder darunter liegen, deshalb liefert die Antwort zusätzlich den Bestpreis und die Einzelstationen.",
        },
        {
          q: "Darf ich die Daten kommerziell nutzen?",
          a: "Die Lizenz erlaubt kommerzielle Nutzung mit Namensnennung. Zusätzlich gelten die Nutzungsbedingungen der Quelle: Abruf nur bei tatsächlicher Nutzeraktion, kein automatisierter Dauerabruf im Hintergrund und keine dauerhafte Speicherung der Preise.",
        },
        {
          q: "Gibt es die Preise für jede Stadt?",
          a: "Der Endpunkt antwortet für jede Stadt im Register, es gibt keine Allowlist. Werte entstehen, sobald im Suchradius geöffnete Tankstellen gemeldet sind, und das ist in Großstädten der Normalfall. Ist dort gerade keine geöffnete Station, meldet die Antwort ehrlich, dass keine Daten vorliegen, statt einen Schätzwert zu erfinden.",
        },
      ],
      datasetName: "Kraftstoffpreise je deutscher Stadt",
      datasetDesc: "Durchschnitts- und Bestpreise für E5, E10 und Diesel je Stadt aus den MTS-K-Meldedaten über Tankerkönig.",
    },
    en: {
      slug: "fuel-prices-api",
      metaTitle: "Fuel price API Germany (MTS-K), key-free",
      h1: "Fuel price API for German cities (MTS-K)",
      lead: "Current fuel prices per city through a free, key-free REST API. The basis is the reported data of the German market transparency unit for fuels, retrieved via Tankerkönig and aggregated per city into average and best prices.",
      dataDesc:
        "Per city the endpoint returns average and minimum prices for Super E5, Super E10 and diesel across the currently open stations around the city, plus the number of stations considered and open, the search radius and the individual stations with brand, address, distance and opening status.",
      sourceName: "Tankerkönig / German market transparency unit for fuels (MTS-K)",
      sourceUrl: "https://creativecommons.tankerkoenig.de/",
      license: "CC BY 4.0",
      licenseUrl: "https://creativecommons.org/licenses/by/4.0/",
      vars: ["Average price E5, E10, diesel", "Best price per grade", "Number of stations in radius", "Number of open stations", "Search radius in kilometres", "Brand and name per station", "Distance to city centre", "Opening status"],
      keywords: ["fuel price API", "petrol station API Germany", "diesel price API", "MTS-K data", "fuel prices open data"],
      coverageNote: "All cities in the register. The city figures are calculated, not reported: they are derived from the open stations inside the search radius around the city coordinate. If no open station is reported there right now, the response honestly states that no data is available instead of inventing a value.",
      faq: [
        {
          q: "How current are the prices?",
          a: "Prices are fetched on request and cached only very briefly. Every response carries the retrieval timestamp. We deliberately do not retain historical prices, as the terms of use of the source prohibit it.",
        },
        {
          q: "Why does the average differ from individual stations?",
          a: "The city value is a calculated mean across the open stations around the city coordinate. Individual stations can be well above or below it, which is why the response also carries the best price and the individual stations.",
        },
        {
          q: "May I use the data commercially?",
          a: "The licence permits commercial use with attribution. The terms of the source apply in addition: retrieval only on actual user action, no automated background polling and no permanent storage of prices.",
        },
        {
          q: "Are prices available for every city?",
          a: "The endpoint answers for every city in the register, there is no allowlist. Values appear as soon as open stations are reported inside the search radius, which is the normal case in larger cities. If no open station is reported there right now, the response honestly reports that no data is available instead of inventing an estimate.",
        },
      ],
      datasetName: "Fuel prices per German city",
      datasetDesc: "Average and best prices for E5, E10 and diesel per city from MTS-K reported data via Tankerkönig.",
    },
  },
  {
    id: "parking",
    endpointId: "getCityParking",
    examplePath: "/api/v1/cities/koeln/parking",
    coverageKey: "parking",
    de: {
      slug: "parken-api",
      metaTitle: "Parken-API Deutschland: Belegung live, keylos",
      h1: "Parkhaus-API für deutsche Städte mit Live-Belegung",
      lead: "Parkhäuser und Parkplätze mit aktueller Belegung über eine kostenlose, keylose REST-API. Quellen sind die offenen Daten der jeweiligen Stadt, vereinheitlicht zu einem gemeinsamen Format über alle Städte hinweg.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt die Parkeinrichtungen mit Name, Kapazität, freien und belegten Plätzen, Auslastung in Prozent, Öffnungsstatus, Koordinaten und dem Zeitpunkt der Messung. Die Städte melden in sehr unterschiedlichen Rohformaten, die Antwort ist dennoch überall gleich aufgebaut.",
      sourceName: "Kommunale Open-Data-Portale und Mobilithek",
      sourceUrl: "https://mobilithek.info/",
      license: "DL-DE Zero 2.0 und DL-DE BY 2.0, je nach Stadt",
      licenseUrl: "https://www.govdata.de/dl-de/zero-2-0",
      vars: ["Name der Parkeinrichtung", "Kapazität", "Freie Plätze", "Belegte Plätze", "Auslastung in Prozent", "Öffnungsstatus", "Koordinaten", "Zeitpunkt der Messung"],
      keywords: ["Parkhaus API", "Parkplatz Belegung API", "Parken Open Data", "freie Parkplätze API", "Parkleitsystem Daten"],
      coverageNote: "Städte mit offener Parkdaten-Schnittstelle. Die Liste wächst, sobald weitere Städte ihre Belegungsdaten öffnen.",
      faq: [
        {
          q: "Wie aktuell ist die Belegung?",
          a: "Die meisten Städte melden im Minutentakt, einzelne seltener. Jede Antwort trägt den Zeitpunkt der Messung, sodass das Alter des Wertes immer sichtbar ist.",
        },
        {
          q: "Welche Lizenz gilt?",
          a: "Das hängt von der liefernden Stadt ab, meist DL-DE Zero 2.0 oder DL-DE BY 2.0. Jede Antwort trägt die konkrete Lizenz und die vorgeschriebene Namensnennung im meta-Block mit.",
        },
        {
          q: "Warum fehlt meine Stadt?",
          a: "Weil sie ihre Belegungsdaten bisher nicht offen bereitstellt. Der Endpunkt meldet dann ehrlich, dass die Datenart für diese Stadt nicht abgedeckt ist, statt einen leeren Datensatz vorzutäuschen.",
        },
        {
          q: "Sind Parkplätze am Straßenrand enthalten?",
          a: "In der Regel nicht. Die Städte melden bewirtschaftete Parkhäuser und Parkplätze mit Zähltechnik. Straßenrandparken wird nur selten erfasst und ist deshalb meist nicht Teil der Daten.",
        },
      ],
      datasetName: "Parkhäuser und Belegung je deutscher Stadt",
      datasetDesc: "Parkeinrichtungen je Stadt mit Kapazität, freien Plätzen, Auslastung und Messzeitpunkt aus kommunalen Open-Data-Quellen.",
    },
    en: {
      slug: "parking-api",
      metaTitle: "Parking API Germany: live occupancy, key-free",
      h1: "Car park API for German cities with live occupancy",
      lead: "Car parks and parking sites with current occupancy through a free, key-free REST API. The sources are the open data of each city, unified into one common format across all cities.",
      dataDesc:
        "Per city the endpoint returns parking facilities with name, capacity, free and occupied spaces, occupancy in percent, opening status, coordinates and the time of measurement. Cities report in very different raw formats, yet the response is structured identically everywhere.",
      sourceName: "Municipal open data portals and Mobilithek",
      sourceUrl: "https://mobilithek.info/",
      license: "DL-DE Zero 2.0 and DL-DE BY 2.0, depending on the city",
      licenseUrl: "https://www.govdata.de/dl-de/zero-2-0",
      vars: ["Facility name", "Capacity", "Free spaces", "Occupied spaces", "Occupancy in percent", "Opening status", "Coordinates", "Time of measurement"],
      keywords: ["parking API", "car park occupancy API", "parking open data Germany", "free parking spaces API"],
      coverageNote: "Cities with an open parking data interface. The list grows as more cities open their occupancy data.",
      faq: [
        {
          q: "How current is the occupancy?",
          a: "Most cities report every minute, some less often. Every response carries the time of measurement, so the age of the value is always visible.",
        },
        {
          q: "Which licence applies?",
          a: "That depends on the supplying city, usually DL-DE Zero 2.0 or DL-DE BY 2.0. Every response carries the specific licence and the required attribution in its meta block.",
        },
        {
          q: "Why is my city missing?",
          a: "Because it does not publish occupancy data openly yet. The endpoint then honestly reports that this data type is not covered for the city instead of faking an empty dataset.",
        },
        {
          q: "Does this include on-street parking?",
          a: "Usually not. Cities report managed car parks and parking sites with counting technology. On-street parking is rarely measured and therefore mostly not part of the data.",
        },
      ],
      datasetName: "Car parks and occupancy per German city",
      datasetDesc: "Parking facilities per city with capacity, free spaces, occupancy and measurement time from municipal open data sources.",
    },
  },
  {
    id: "road-events",
    endpointId: "getCityRoadEvents",
    examplePath: "/api/v1/cities/koeln/road-events",
    coverageKey: "road-events",
    de: {
      slug: "baustellen-api",
      metaTitle: "Baustellen-API Deutschland: Sperrungen, keylos",
      h1: "Baustellen- und Sperrungs-API für deutsche Städte",
      lead: "Innerstädtische Baustellen, Sperrungen und Verkehrsereignisse über eine kostenlose, keylose REST-API. Quellen sind die Verkehrsportale der Städte, vereinheitlicht zu einem gemeinsamen Format mit Zeitraum, Art und Ort je Ereignis.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt die gemeldeten Ereignisse mit Bezeichnung, Beginn und Ende, Art des Ereignisses als Klartext, Koordinaten und der meldenden Stadtquelle. Für Autobahnen gibt es einen eigenen Endpunkt auf Basis der Daten der Autobahn GmbH.",
      sourceName: "Verkehrsportale der Städte und Mobilithek",
      sourceUrl: "https://mobilithek.info/",
      license: "DL-DE Zero 2.0 und DL-DE BY 2.0, je nach Stadt",
      licenseUrl: "https://www.govdata.de/dl-de/zero-2-0",
      vars: ["Bezeichnung des Ereignisses", "Beginn", "Ende", "Art des Ereignisses", "Koordinaten", "Meldende Stadtquelle"],
      keywords: ["Baustellen API", "Verkehrsmeldungen API", "Straßensperrungen Daten", "Baustellen Open Data", "Verkehrsbehinderungen API"],
      coverageNote: "Städte mit offener Baustellen-Schnittstelle. Weitere Städte kommen dazu, sobald sie ihre Verkehrsmeldungen öffnen.",
      faq: [
        {
          q: "Wie aktuell sind die Meldungen?",
          a: "Die Städte melden meist im Minutentakt. Fällt eine Quelle kurz aus, liefert die API bis zu sechs Stunden den zuletzt bekannten Stand und kennzeichnet das im meta-Block, statt mit einem Fehler abzubrechen.",
        },
        {
          q: "Sind Autobahn-Baustellen enthalten?",
          a: "Nein, dieser Endpunkt deckt das Stadtgebiet ab. Für Autobahnen gibt es einen eigenen Endpunkt auf Basis der offenen Daten der Autobahn GmbH.",
        },
        {
          q: "Was bedeutet die Art des Ereignisses?",
          a: "Die Städte melden Zahlencodes für Baustelle, Sperrung, Umleitung und Ähnliches. Die API liefert zusätzlich einen deutschen Klartext, sodass der Code nicht nachgeschlagen werden muss.",
        },
        {
          q: "Warum liegen manche Ereignisse in der Vergangenheit?",
          a: "Langlaufende Baustellen werden mit ihrem tatsächlichen Beginn gemeldet, teils Jahre zurück. Entscheidend ist das Ende: Ereignisse bleiben gelistet, solange sie laut Stadt andauern.",
        },
      ],
      datasetName: "Baustellen und Sperrungen je deutscher Stadt",
      datasetDesc: "Innerstädtische Baustellen, Sperrungen und Verkehrsereignisse je Stadt mit Zeitraum, Art und Koordinaten aus kommunalen Verkehrsportalen.",
    },
    en: {
      slug: "roadworks-api",
      metaTitle: "Roadworks API Germany: closures, key-free",
      h1: "Roadworks and closure API for German cities",
      lead: "Urban roadworks, closures and traffic events through a free, key-free REST API. The sources are the traffic portals of the cities, unified into one common format with period, type and location per event.",
      dataDesc:
        "Per city the endpoint returns the reported events with label, start and end, the type of event in plain text, coordinates and the reporting city source. For motorways there is a separate endpoint based on data from Autobahn GmbH.",
      sourceName: "City traffic portals and Mobilithek",
      sourceUrl: "https://mobilithek.info/",
      license: "DL-DE Zero 2.0 and DL-DE BY 2.0, depending on the city",
      licenseUrl: "https://www.govdata.de/dl-de/zero-2-0",
      vars: ["Event label", "Start", "End", "Type of event", "Coordinates", "Reporting city source"],
      keywords: ["roadworks API", "traffic messages API Germany", "road closures data", "roadworks open data"],
      coverageNote: "Cities with an open roadworks interface. More cities follow as they open their traffic messages.",
      faq: [
        {
          q: "How current are the messages?",
          a: "Cities mostly report every minute. If a source briefly fails, the API serves the last known state for up to six hours and marks this in the meta block instead of failing with an error.",
        },
        {
          q: "Does this include motorway roadworks?",
          a: "No, this endpoint covers the city area. For motorways there is a separate endpoint based on the open data of Autobahn GmbH.",
        },
        {
          q: "What does the type of event mean?",
          a: "Cities report numeric codes for roadworks, closure, diversion and similar. The API additionally provides plain text, so the code does not have to be looked up.",
        },
        {
          q: "Why are some events in the past?",
          a: "Long-running roadworks are reported with their actual start, sometimes years back. What matters is the end: events stay listed as long as the city reports them as ongoing.",
        },
      ],
      datasetName: "Roadworks and closures per German city",
      datasetDesc: "Urban roadworks, closures and traffic events per city with period, type and coordinates from municipal traffic portals.",
    },
  },
  {
    id: "water-level",
    endpointId: "getCityWaterLevel",
    examplePath: "/api/v1/cities/koeln/water-level",
    coverageKey: "water-level",
    de: {
      slug: "pegelstaende-api",
      metaTitle: "Pegelstände-API Deutschland (WSV), keylos",
      h1: "Pegelstands-API für deutsche Städte (PEGELONLINE)",
      lead: "Aktuelle Wasserstände an Bundeswasserstraßen je Stadt über eine kostenlose, keylose REST-API. Quelle ist PEGELONLINE der Wasserstraßen- und Schifffahrtsverwaltung des Bundes, ergänzt um die amtlichen Hochwasserlagen der Länder.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt die nächstgelegene Pegelmessstelle mit Name des Pegels, Gewässer, aktuellem Messwert und Einheit sowie dem Zeitpunkt der Messung. Ein zweiter Endpunkt liefert die amtlichen Hochwasserwarnungen der Länder-Hochwasserzentralen.",
      sourceName: "PEGELONLINE, Wasserstraßen- und Schifffahrtsverwaltung des Bundes (WSV)",
      sourceUrl: "https://www.pegelonline.wsv.de/",
      license: "DL-DE Zero 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/zero-2-0",
      vars: ["Name der Pegelmessstelle", "Gewässer", "Wasserstand", "Einheit (meist Zentimeter)", "Zeitpunkt der Messung"],
      keywords: ["Pegelstand API", "Wasserstand API Deutschland", "PEGELONLINE API", "Hochwasser Daten API", "Pegel Open Data"],
      coverageNote: "80 Städte mit einer Pegelmessstelle in erreichbarer Nähe. Städte ohne Bundeswasserstraße in der Umgebung melden ehrlich, dass keine Daten vorliegen.",
      faq: [
        {
          q: "Wie aktuell sind die Wasserstände?",
          a: "PEGELONLINE aktualisiert im Viertelstundentakt. Jede Antwort trägt den Zeitpunkt der Messung, sodass das Alter des Wertes immer sichtbar ist.",
        },
        {
          q: "Ist der Wert eine Höhe über Normalnull?",
          a: "Nein. Der Pegelstand ist die Höhe über dem Pegelnullpunkt der jeweiligen Messstelle, meist in Zentimetern. Werte verschiedener Pegel sind deshalb nicht direkt miteinander vergleichbar.",
        },
        {
          q: "Bekomme ich auch Hochwasserwarnungen?",
          a: "Ja, über einen eigenen Endpunkt. Er liefert die amtlichen Lagen der Länder-Hochwasserzentralen mit dem jeweiligen Stand, getrennt von den reinen Messwerten.",
        },
        {
          q: "Warum fehlt meine Stadt?",
          a: "Weil in erreichbarer Nähe keine Messstelle einer Bundeswasserstraße liegt. Binnenstädte ohne größeren Fluss haben deshalb keine Werte, und die Antwort sagt das offen.",
        },
      ],
      datasetName: "Pegelstände je deutscher Stadt",
      datasetDesc: "Aktuelle Wasserstände der nächstgelegenen Pegelmessstelle je Stadt mit Gewässer, Messwert und Zeitpunkt aus PEGELONLINE.",
    },
    en: {
      slug: "water-level-api",
      metaTitle: "Water level API Germany (WSV), key-free",
      h1: "Water level API for German cities (PEGELONLINE)",
      lead: "Current water levels on federal waterways per city through a free, key-free REST API. The source is PEGELONLINE of the German Federal Waterways and Shipping Administration, complemented by the official flood situations of the states.",
      dataDesc:
        "Per city the endpoint returns the nearest gauging station with the name of the gauge, the body of water, the current reading and unit as well as the time of measurement. A second endpoint provides the official flood warnings of the state flood centres.",
      sourceName: "PEGELONLINE, German Federal Waterways and Shipping Administration (WSV)",
      sourceUrl: "https://www.pegelonline.wsv.de/",
      license: "DL-DE Zero 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/zero-2-0",
      vars: ["Name of the gauging station", "Body of water", "Water level", "Unit (usually centimetres)", "Time of measurement"],
      keywords: ["water level API", "gauge API Germany", "PEGELONLINE API", "flood data API", "water level open data"],
      coverageNote: "80 cities with a gauging station within reach. Cities without a federal waterway nearby honestly report that no data is available.",
      faq: [
        {
          q: "How current are the water levels?",
          a: "PEGELONLINE updates every quarter of an hour. Every response carries the time of measurement, so the age of the value is always visible.",
        },
        {
          q: "Is the value a height above sea level?",
          a: "No. The water level is the height above the gauge datum of the respective station, usually in centimetres. Values from different gauges are therefore not directly comparable.",
        },
        {
          q: "Do I also get flood warnings?",
          a: "Yes, through a separate endpoint. It provides the official situations of the state flood centres with their timestamp, kept apart from the pure readings.",
        },
        {
          q: "Why is my city missing?",
          a: "Because there is no gauging station of a federal waterway within reach. Inland cities without a major river therefore have no values, and the response says so openly.",
        },
      ],
      datasetName: "Water levels per German city",
      datasetDesc: "Current water levels of the nearest gauging station per city with body of water, reading and timestamp from PEGELONLINE.",
    },
  },
  {
    id: "weather-warnings",
    endpointId: "getCityWeatherWarnings",
    examplePath: "/api/v1/cities/koeln/weather-warnings",
    coverageKey: "all",
    de: {
      slug: "unwetterwarnungen-api",
      metaTitle: "Unwetterwarnungen-API Deutschland (DWD), keylos",
      h1: "Unwetterwarnungen-API für deutsche Städte (DWD)",
      lead: "Amtliche Wetterwarnungen für 84 deutsche Großstädte über eine kostenlose, keylose REST-API. Quelle ist der Deutsche Wetterdienst, ergänzt um die Bevölkerungsschutz-Warnungen des Bundesamts für Bevölkerungsschutz über einen zweiten Endpunkt.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt die aktuell gültigen Warnungen mit Warnstufe, Ereignisart, Beginn und Ende, Beschreibung und Verhaltenshinweis, dazu die Anzahl der Warnungen und die höchste anliegende Stufe. Vorabinformationen zu schwerem Unwetter werden getrennt ausgewiesen.",
      sourceName: "Deutscher Wetterdienst (DWD)",
      sourceUrl: "https://www.dwd.de/",
      license: "DL-DE BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Warnstufe", "Ereignisart", "Beginn und Ende", "Beschreibung", "Verhaltenshinweis", "Anzahl der Warnungen", "Höchste anliegende Stufe", "Vorabinformationen"],
      keywords: ["Unwetterwarnung API", "Wetterwarnung API Deutschland", "DWD Warnungen API", "Amtliche Warnungen Daten", "Warnstufen API"],
      coverageNote: "Alle 84 Städte, da der DWD flächendeckend für ganz Deutschland warnt.",
      faq: [
        {
          q: "Wie schnell sind neue Warnungen verfügbar?",
          a: "Die Warnlage wird minütlich abgeglichen. Fällt die Quelle kurz aus, liefert die API bis zu sechs Stunden den zuletzt bekannten Stand und kennzeichnet das, denn eine veraltete Warnung ist besser als gar keine Antwort.",
        },
        {
          q: "Was bedeuten die Warnstufen?",
          a: "Der DWD unterscheidet vier Stufen von Wetterwarnung über markantes Wetter und Unwetter bis zu extremem Unwetter. Die Antwort liefert die Stufe als Zahl und zusätzlich die höchste anliegende Stufe je Stadt.",
        },
        {
          q: "Sind auch Katastrophenwarnungen enthalten?",
          a: "Nicht in diesem Endpunkt. Für Bevölkerungsschutz-Warnungen wie Gefahrstoffaustritt oder Ausfall der Trinkwasserversorgung gibt es einen eigenen Endpunkt auf Basis des Warnsystems des Bundesamts für Bevölkerungsschutz.",
        },
        {
          q: "Darf ich die Warnungen in einer eigenen App anzeigen?",
          a: "Ja, mit Namensnennung des Deutschen Wetterdienstes. Bei sicherheitsrelevanten Anwendungen sollte zusätzlich immer die amtliche Quelle verlinkt werden, damit Nutzer die Warnung im Original prüfen können.",
        },
      ],
      datasetName: "Amtliche Wetterwarnungen je deutscher Stadt",
      datasetDesc: "Gültige DWD-Wetterwarnungen je Stadt mit Warnstufe, Ereignisart, Zeitraum und Verhaltenshinweis.",
    },
    en: {
      slug: "weather-warnings-api",
      metaTitle: "Weather warning API Germany (DWD), key-free",
      h1: "Weather warning API for German cities (DWD)",
      lead: "Official weather warnings for 84 major German cities through a free, key-free REST API. The source is the German Weather Service, complemented by the civil protection warnings of the Federal Office of Civil Protection through a second endpoint.",
      dataDesc:
        "Per city the endpoint returns the currently valid warnings with severity level, event type, start and end, description and instruction, plus the number of warnings and the highest level in effect. Advance information on severe weather is reported separately.",
      sourceName: "German Weather Service (DWD)",
      sourceUrl: "https://www.dwd.de/",
      license: "DL-DE BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Severity level", "Event type", "Start and end", "Description", "Instruction", "Number of warnings", "Highest level in effect", "Advance information"],
      keywords: ["weather warning API", "severe weather API Germany", "DWD warnings API", "official warnings data"],
      coverageNote: "All 84 cities, as the DWD warns across the whole of Germany.",
      faq: [
        {
          q: "How quickly are new warnings available?",
          a: "The warning situation is reconciled every minute. If the source briefly fails, the API serves the last known state for up to six hours and marks it, because an ageing warning is better than no answer at all.",
        },
        {
          q: "What do the severity levels mean?",
          a: "The DWD distinguishes four levels, from weather warning through marked weather and severe weather to extremely severe weather. The response carries the level as a number and additionally the highest level in effect per city.",
        },
        {
          q: "Does this include disaster warnings?",
          a: "Not in this endpoint. For civil protection warnings such as hazardous material release or drinking water failure there is a separate endpoint based on the warning system of the Federal Office of Civil Protection.",
        },
        {
          q: "May I display the warnings in my own app?",
          a: "Yes, with attribution to the German Weather Service. For safety-critical applications the official source should always be linked as well, so users can check the warning in its original form.",
        },
      ],
      datasetName: "Official weather warnings per German city",
      datasetDesc: "Valid DWD weather warnings per city with severity level, event type, period and instruction.",
    },
  },
  {
    id: "charging",
    endpointId: "getCityCharging",
    examplePath: "/api/v1/cities/koeln/charging",
    coverageKey: "all",
    de: {
      slug: "ladesaeulen-api",
      metaTitle: "Ladesäulen-API Deutschland (BNetzA), keylos",
      h1: "Ladesäulen-API für deutsche Städte (Bundesnetzagentur)",
      lead: "Öffentliche Ladeinfrastruktur für 84 deutsche Großstädte über eine kostenlose, keylose REST-API. Quelle ist das Ladesäulenregister der Bundesnetzagentur, ausgeliefert in einem einheitlichen JSON-Envelope mit Quelle, Lizenz und Zeitstempel je Antwort.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt alle gemeldeten Ladepunkte mit Betreiber, Ladeleistung in Kilowatt, Ladeart, Anzahl der Ladepunkte je Standort, Betriebsstatus und Koordinaten. Für Hamburg gibt es über einen separaten Endpunkt zusätzlich die minutenaktuelle Belegung je Ladepunkt.",
      sourceName: "Bundesnetzagentur (Ladesäulenregister)",
      sourceUrl: "https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/E-Mobilitaet/start.html",
      license: "CC BY 4.0",
      licenseUrl: "https://creativecommons.org/licenses/by/4.0/",
      vars: ["Betreiber", "Ladeleistung (kW)", "Ladeart (Normal- oder Schnellladung)", "Anzahl Ladepunkte", "Betriebsstatus", "Koordinaten", "Postleitzahl und Ort", "Straße und Hausnummer"],
      keywords: ["Ladesäulen API", "Ladesäulenregister API", "Elektromobilität Daten Deutschland", "Ladepunkte API", "Ladeinfrastruktur Open Data"],
      coverageNote: "Alle 84 Städte, da das Ladesäulenregister bundesweit geführt wird.",
      faq: [
        {
          q: "Sind die Ladesäulen-Daten aktuell?",
          a: "Das Register der Bundesnetzagentur ist ein Meldebestand und wird regelmäßig aktualisiert, nicht sekundengenau. Jede Antwort trägt den Abrufzeitpunkt, sodass das Alter der Daten immer erkennbar ist.",
        },
        {
          q: "Sehe ich, ob eine Ladesäule gerade frei ist?",
          a: "Im Register nicht, das enthält den Bestand und den gemeldeten Betriebsstatus. Für Hamburg liefert ein separater Endpunkt die minutenaktuelle Belegung je Ladepunkt aus offenen Daten der Hamburger Energienetze.",
        },
        {
          q: "Brauche ich einen API-Schlüssel?",
          a: "Nein. Die Abfrage ist ohne Anmeldung und ohne Schlüssel möglich und kommerziell nutzbar, solange die Bundesnetzagentur als Quelle genannt wird.",
        },
        {
          q: "Wie unterscheide ich Schnelllader von Normalladern?",
          a: "Über das Feld zur Ladeart und die Ladeleistung in Kilowatt. Alles ab 22 kW gilt üblicherweise als Schnellladeeinrichtung, das Register weist die Einstufung zusätzlich als Text aus.",
        },
      ],
      datasetName: "Ladesäulen je deutscher Stadt",
      datasetDesc: "Öffentliche Ladepunkte je Stadt mit Betreiber, Ladeleistung, Ladeart und Koordinaten aus dem Ladesäulenregister der Bundesnetzagentur.",
    },
    en: {
      slug: "charging-stations-api",
      metaTitle: "EV charging API Germany (BNetzA), key-free",
      h1: "EV charging station API for German cities (BNetzA)",
      lead: "Public charging infrastructure for 84 major German cities through a free, key-free REST API. The source is the charging station register of the Federal Network Agency, served in a uniform JSON envelope with source, licence and timestamp per response.",
      dataDesc:
        "Per city the endpoint returns all registered charging points with operator, charging power in kilowatts, charging type, number of points per site, operating status and coordinates. For Hamburg a separate endpoint additionally provides minute-fresh occupancy per charging point.",
      sourceName: "Federal Network Agency (charging station register)",
      sourceUrl: "https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/E-Mobilitaet/start.html",
      license: "CC BY 4.0",
      licenseUrl: "https://creativecommons.org/licenses/by/4.0/",
      vars: ["Operator", "Charging power (kW)", "Charging type (normal or fast)", "Number of charging points", "Operating status", "Coordinates", "Post code and place", "Street and house number"],
      keywords: ["EV charging API", "charging station API Germany", "electromobility data Germany", "charging points API", "charging infrastructure open data"],
      coverageNote: "All 84 cities, as the charging station register is maintained nationwide.",
      faq: [
        {
          q: "How current is the charging station data?",
          a: "The Federal Network Agency register is a reported inventory and is updated regularly, not second by second. Every response carries the retrieval timestamp, so the age of the data is always visible.",
        },
        {
          q: "Can I see whether a charging point is free right now?",
          a: "Not in the register, which holds the inventory and the reported operating status. For Hamburg a separate endpoint provides minute-fresh occupancy per charging point from open data of Hamburger Energienetze.",
        },
        {
          q: "Do I need an API key?",
          a: "No. Queries work without registration and without a key and may be used commercially as long as the Federal Network Agency is credited as the source.",
        },
        {
          q: "How do I tell fast chargers from normal ones?",
          a: "Through the charging type field and the power in kilowatts. Anything from 22 kW upwards is commonly considered fast charging, and the register also states the classification as text.",
        },
      ],
      datasetName: "EV charging points per German city",
      datasetDesc: "Public charging points per city with operator, charging power, charging type and coordinates from the German Federal Network Agency register.",
    },
  },
  {
    id: "weather",
    endpointId: "getCityWeather",
    examplePath: "/api/v1/cities/berlin/weather",
    coverageKey: "all",
    de: {
      slug: "wetter-api",
      metaTitle: "Wetter-API Deutschland (DWD): kostenlos und keylos",
      h1: "Wetter-API für deutsche Städte (DWD)",
      lead: "Aktuelle Wetterdaten für 84 deutsche Großstädte über eine kostenlose, keylose REST-API. Quelle ist der Deutsche Wetterdienst (DWD), ausgeliefert in einem einheitlichen JSON-Envelope mit Quelle, Lizenz und Zeitstempel je Antwort.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt die nächstgelegene DWD-Messung: Lufttemperatur, Luftfeuchte, Windgeschwindigkeit und Wetterlage, dazu Beobachtungszeitpunkt und Stations-ID. Über einen separaten Endpunkt gibt es amtliche DWD-Wetterwarnungen.",
      sourceName: "Deutscher Wetterdienst (DWD)",
      sourceUrl: "https://www.dwd.de/",
      license: "DL-DE BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Lufttemperatur (Grad Celsius)", "Relative Luftfeuchte", "Windgeschwindigkeit", "Wetterlage", "Beobachtungszeitpunkt", "Stations-ID"],
      keywords: ["Wetter API Deutschland", "DWD API", "keylose Wetter API", "Wetterdaten API kostenlos", "Wetter API JSON", "Wetterstation API"],
      coverageNote: "Wetterdaten sind für alle 84 abgedeckten Großstädte verfügbar (nächstgelegene DWD-Station).",
      faq: [
        { q: "Brauche ich einen API-Schlüssel für die Wetter-API?", a: "Nein. Die InfraNode-Wetter-API ist keylos und kostenlos. Ein einfacher GET-Request ohne Anmeldung genügt, das Rate-Limit liegt bei 300 Anfragen pro Minute und IP." },
        { q: "Woher kommen die Wetterdaten?", a: "Die Daten stammen vom Deutschen Wetterdienst (DWD) und werden unverändert unter der Lizenz DL-DE BY 2.0 durchgereicht. Jede API-Antwort enthält Quelle, Lizenz-URL und Beobachtungszeitpunkt." },
        { q: "Wie aktuell sind die Werte?", a: "Die API liefert die jeweils jüngste verfügbare DWD-Beobachtung. Der Zeitpunkt steht als observed_at in jeder Antwort, dazu ein Cache-Status im meta-Block." },
      ],
      datasetName: "InfraNode Wetterdaten deutscher Großstädte (DWD)",
      datasetDesc: "Aktuelle Wetterbeobachtungen (Temperatur, Luftfeuchte, Wind, Wetterlage) für 84 deutsche Großstädte aus DWD-Stationsdaten, kostenlos und keylos über eine REST-API als JSON.",
    },
    en: {
      slug: "weather-api",
      metaTitle: "Germany Weather API (DWD): free and keyless, per city",
      h1: "Weather API for German cities (DWD)",
      lead: "Current weather data for 84 major German cities through a free, keyless REST API. The source is the German Weather Service (DWD), delivered in one consistent JSON envelope with source, license and timestamp on every response.",
      dataDesc:
        "For each city the endpoint returns the nearest DWD observation: air temperature, humidity, wind speed and weather condition, plus the observation time and station id. A separate endpoint serves official DWD weather warnings.",
      sourceName: "German Weather Service (DWD)",
      sourceUrl: "https://www.dwd.de/",
      license: "DL-DE BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Air temperature (degrees Celsius)", "Relative humidity", "Wind speed", "Weather condition", "Observation time", "Station id"],
      keywords: ["weather API Germany", "DWD API", "keyless weather API", "free weather data API", "weather API JSON", "German weather API"],
      coverageNote: "Weather data is available for all 84 covered cities (nearest DWD station).",
      faq: [
        { q: "Do I need an API key for the weather API?", a: "No. The InfraNode weather API is keyless and free. A simple GET request without sign-up is enough; the rate limit is 300 requests per minute per IP." },
        { q: "Where does the weather data come from?", a: "Data comes from the German Weather Service (DWD) and is passed through unchanged under the DL-DE BY 2.0 license. Every API response carries the source, license URL and observation time." },
        { q: "How current are the values?", a: "The API returns the most recent available DWD observation. The time is exposed as observed_at on every response, with a cache status in the meta block." },
      ],
      datasetName: "InfraNode weather data for German cities (DWD)",
      datasetDesc: "Current weather observations (temperature, humidity, wind, condition) for 84 major German cities from DWD station data, free and keyless via a JSON REST API.",
    },
  },
  {
    id: "air-quality",
    endpointId: "getCityAirUba",
    examplePath: "/api/v1/cities/berlin/air-uba",
    coverageKey: "all",
    de: {
      slug: "luftqualitaet-api",
      metaTitle: "Luftqualitäts-API Deutschland (UBA), keylos",
      h1: "Luftqualitäts-API für deutsche Städte (UBA)",
      lead: "Aktuelle Luftqualitätsdaten für deutsche Großstädte über eine kostenlose, keylose REST-API. Quelle ist das Umweltbundesamt (UBA) mit seinem amtlichen Messnetz, einheitlich als JSON mit Quelle und Lizenz je Antwort.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt die Messwerte der nächstgelegenen UBA-Station: Feinstaub PM10 und PM2.5, Stickstoffdioxid NO2, Ozon O3 und Schwefeldioxid SO2, jeweils mit Messzeitpunkt und Stationsbezug.",
      sourceName: "Umweltbundesamt (UBA)",
      sourceUrl: "https://www.umweltbundesamt.de/",
      license: "DL-DE BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Feinstaub PM10", "Feinstaub PM2.5", "Stickstoffdioxid (NO2)", "Ozon (O3)", "Schwefeldioxid (SO2)", "Messzeitpunkt", "Messstation"],
      keywords: ["Luftqualität API Deutschland", "Feinstaub API", "UBA API", "Luftqualitäts API kostenlos", "NO2 PM10 API", "Air Quality API Germany"],
      coverageNote: "Luftqualitätsdaten richten sich nach dem UBA-Messnetz; abgefragt wird die jeweils nächstgelegene Station.",
      faq: [
        { q: "Ist die Luftqualitäts-API kostenlos und ohne Schlüssel nutzbar?", a: "Ja. Die API ist keylos und kostenlos, ein GET-Request ohne Anmeldung genügt. Das Rate-Limit beträgt 300 Anfragen pro Minute und IP." },
        { q: "Welche Schadstoffe sind enthalten?", a: "Feinstaub PM10 und PM2.5, Stickstoffdioxid NO2, Ozon O3 und Schwefeldioxid SO2 aus dem Messnetz des Umweltbundesamts, mit Messzeitpunkt und Stationsbezug je Wert." },
        { q: "Welche Lizenz gilt für die Luftdaten?", a: "Die UBA-Daten werden unter DL-DE BY 2.0 durchgereicht. Die Lizenz-URL und der Attributionstext stehen in jeder API-Antwort im attribution-Block." },
      ],
      datasetName: "InfraNode Luftqualitätsdaten deutscher Großstädte (UBA)",
      datasetDesc: "Aktuelle Luftqualitätswerte (PM10, PM2.5, NO2, O3, SO2) für deutsche Großstädte aus dem Messnetz des Umweltbundesamts, kostenlos und keylos über eine REST-API als JSON.",
    },
    en: {
      slug: "air-quality-api",
      metaTitle: "Germany Air Quality API (UBA): free and keyless",
      h1: "Air quality API for German cities (UBA)",
      lead: "Current air quality data for major German cities through a free, keyless REST API. The source is the German Environment Agency (UBA) with its official monitoring network, delivered as consistent JSON with source and license on every response.",
      dataDesc:
        "For each city the endpoint returns readings from the nearest UBA station: particulate matter PM10 and PM2.5, nitrogen dioxide NO2, ozone O3 and sulphur dioxide SO2, each with measurement time and station reference.",
      sourceName: "German Environment Agency (UBA)",
      sourceUrl: "https://www.umweltbundesamt.de/en",
      license: "DL-DE BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Particulate matter PM10", "Particulate matter PM2.5", "Nitrogen dioxide (NO2)", "Ozone (O3)", "Sulphur dioxide (SO2)", "Measurement time", "Monitoring station"],
      keywords: ["air quality API Germany", "particulate matter API", "UBA API", "free air quality API", "NO2 PM10 API", "German air quality data API"],
      coverageNote: "Air quality data follows the UBA monitoring network; the nearest station is queried per city.",
      faq: [
        { q: "Is the air quality API free and usable without a key?", a: "Yes. The API is keyless and free; a GET request without sign-up is enough. The rate limit is 300 requests per minute per IP." },
        { q: "Which pollutants are included?", a: "Particulate matter PM10 and PM2.5, nitrogen dioxide NO2, ozone O3 and sulphur dioxide SO2 from the German Environment Agency network, with measurement time and station reference per value." },
        { q: "Which license applies to the air data?", a: "UBA data is passed through under DL-DE BY 2.0. The license URL and attribution text are included in every API response in the attribution block." },
      ],
      datasetName: "InfraNode air quality data for German cities (UBA)",
      datasetDesc: "Current air quality values (PM10, PM2.5, NO2, O3, SO2) for major German cities from the German Environment Agency network, free and keyless via a JSON REST API.",
    },
  },
  {
    id: "electricity-price",
    endpointId: "getCityPowerPrice",
    examplePath: "/api/v1/cities/berlin/power-price",
    coverageKey: "all",
    de: {
      slug: "strompreis-api",
      metaTitle: "Strompreis-API Deutschland (SMARD): Day-Ahead, keylos",
      h1: "Strompreis-API für Deutschland (SMARD)",
      lead: "Der bundesweite Day-Ahead-Börsenstrompreis über eine kostenlose, keylose REST-API. Quelle ist SMARD der Bundesnetzagentur, einheitlich als JSON mit Quelle, Lizenz und Zeitstempel je Antwort.",
      dataDesc:
        "Der Endpunkt liefert den deutschlandweiten Day-Ahead-Börsenstrompreis (EUR pro MWh) als Tageswert. Da es ein bundesweiter Preis ist, ist der Wert für jede Stadt identisch, abrufbar bequem über den jeweiligen Stadt-Slug. Ein zweiter Endpunkt liefert die Netzlast (Stromverbrauch) der Regelzone je Stadt.",
      sourceName: "SMARD, Bundesnetzagentur",
      sourceUrl: "https://www.smard.de/",
      license: "DL-DE BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Day-Ahead-Börsenstrompreis (EUR/MWh)", "Bezugszeitpunkt", "Netzlast der Regelzone (über power-load)"],
      keywords: ["Strompreis API", "SMARD API", "Börsenstrompreis API", "Day Ahead Strompreis API", "Strompreis API kostenlos", "Energiedaten API Deutschland"],
      coverageNote: "Der Day-Ahead-Preis ist bundesweit, also für alle 84 Städte über denselben Wert abrufbar. Die Netzlast (power-load) bezieht sich auf die jeweilige Regelzone.",
      faq: [
        { q: "Ist die Strompreis-API kostenlos und keylos?", a: "Ja. Kein Schlüssel, keine Anmeldung, kostenlos, ein GET-Request genügt. Das Rate-Limit beträgt 300 Anfragen pro Minute und IP." },
        { q: "Ist der Strompreis pro Stadt unterschiedlich?", a: "Nein. Der Day-Ahead-Börsenstrompreis gilt für ganz Deutschland einheitlich. Der Abruf über einen Stadt-Slug ist nur bequemer Zugang zu demselben bundesweiten Wert." },
        { q: "Eignet sich die API für Smart Home oder dynamische Tarife?", a: "Ja. Der Tageswert lässt sich keylos abrufen und etwa in Home Assistant oder ioBroker einbinden, um Verbraucher in günstige Stunden zu legen." },
      ],
      datasetName: "InfraNode Strompreisdaten Deutschland (SMARD)",
      datasetDesc: "Bundesweiter Day-Ahead-Börsenstrompreis und Netzlast aus SMARD-Daten der Bundesnetzagentur, kostenlos und keylos über eine REST-API als JSON.",
    },
    en: {
      slug: "electricity-price-api",
      metaTitle: "Germany Electricity Price API (SMARD), keyless",
      h1: "Electricity price API for Germany (SMARD)",
      lead: "The nationwide day-ahead spot electricity price through a free, keyless REST API. The source is SMARD by the Federal Network Agency, delivered as consistent JSON with source, license and timestamp on every response.",
      dataDesc:
        "The endpoint returns the Germany-wide day-ahead spot electricity price (EUR per MWh) as a daily value. Because it is a national price, the value is identical for every city, conveniently retrievable via each city slug. A second endpoint returns the grid load (electricity consumption) of the control zone per city.",
      sourceName: "SMARD, Federal Network Agency",
      sourceUrl: "https://www.smard.de/en",
      license: "DL-DE BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Day-ahead spot electricity price (EUR/MWh)", "Reference time", "Grid load of the control zone (via power-load)"],
      keywords: ["electricity price API", "SMARD API", "spot electricity price API", "day ahead electricity price API", "free electricity price API", "Germany energy data API"],
      coverageNote: "The day-ahead price is nationwide, so the same value is retrievable for all 84 cities. Grid load (power-load) refers to the respective control zone.",
      faq: [
        { q: "Is the electricity price API free and keyless?", a: "Yes. No key, no sign-up, free, a single GET request is enough. The rate limit is 300 requests per minute per IP." },
        { q: "Does the electricity price differ per city?", a: "No. The day-ahead spot price is uniform across Germany. Retrieving it via a city slug is just convenient access to the same national value." },
        { q: "Is the API suitable for smart home or dynamic tariffs?", a: "Yes. The daily value can be fetched keyless and integrated into Home Assistant or ioBroker, for example to shift loads into cheaper hours." },
      ],
      datasetName: "InfraNode electricity price data Germany (SMARD)",
      datasetDesc: "Nationwide day-ahead spot electricity price and grid load from SMARD data of the Federal Network Agency, free and keyless via a JSON REST API.",
    },
  },
  {
    id: "land-values",
    endpointId: "getCityLandValues",
    examplePath: "/api/v1/cities/berlin/land-values",
    coverageKey: "land-values",
    de: {
      slug: "bodenrichtwerte-api",
      metaTitle: "Bodenrichtwerte-API Deutschland (BORIS), keylos",
      h1: "Bodenrichtwerte-API für deutsche Städte (BORIS)",
      lead: "Amtliche Bodenrichtwerte je Stadt über eine kostenlose, keylose REST-API. Quelle sind die BORIS-Geodatendienste der Länder, aggregiert zu einer Bauland-Kennzahl je Stadt und einheitlich als JSON ausgeliefert.",
      dataDesc:
        "Pro abgedeckter Stadt liefert der Endpunkt eine Bauland-Kennzahl: Median, Minimum und Maximum der Bodenrichtwerte in EUR pro Quadratmeter, Anzahl der Zonen und den Stichtag. Gefiltert auf Bauland (Wohnen, Misch, Gewerbe), damit Wald- und Wasserzonen den Wert nicht verzerren.",
      sourceName: "BORIS (Bodenrichtwertinformationssysteme der Länder)",
      sourceUrl: "https://www.bodenrichtwerte-boris.de/",
      license: "DL-DE Zero 2.0 bzw. DL-DE BY 2.0 (je Land)",
      licenseUrl: "https://www.govdata.de/dl-de/zero-2-0",
      vars: ["Median-Bodenrichtwert (EUR/m²)", "Minimum-Bodenrichtwert", "Maximum-Bodenrichtwert", "Anzahl Bodenrichtwertzonen", "Stichtag"],
      keywords: ["Bodenrichtwerte API", "BORIS API", "Bodenrichtwert Deutschland API", "Grundstückspreise API", "Bauland API", "Immobiliendaten API"],
      coverageNote: "Bodenrichtwerte sind dort verfügbar, wo das jeweilige Land einen offenen BORIS-Dienst bereitstellt.",
      faq: [
        { q: "Ist die Bodenrichtwerte-API kostenlos und keylos?", a: "Ja. Kein Schlüssel, keine Anmeldung, kostenlos, ein GET-Request genügt. Das Rate-Limit beträgt 300 Anfragen pro Minute und IP." },
        { q: "Was bedeutet die Bauland-Kennzahl?", a: "Es ist der Median der Bodenrichtwerte einer Stadt, gefiltert auf Bauland (Wohnen, Misch, Gewerbe), plus Minimum, Maximum, Zonenzahl und Stichtag. So bleibt der Wert aussagekräftig und nicht durch Wald- oder Wasserflächen verzerrt." },
        { q: "Warum ist nicht jede Stadt abgedeckt?", a: "Bodenrichtwerte werden je Bundesland bereitgestellt. Wo ein Land keinen offenen BORIS-Dienst anbietet (etwa lizenzbeschränkt), antwortet die API ehrlich mit not_covered statt zu raten." },
      ],
      datasetName: "InfraNode Bodenrichtwerte deutscher Städte (BORIS)",
      datasetDesc: "Amtliche Bodenrichtwerte als Bauland-Kennzahl (Median, Minimum, Maximum, Zonen, Stichtag) je Stadt aus BORIS-Diensten der Länder, kostenlos und keylos über eine REST-API als JSON.",
    },
    en: {
      slug: "land-values-api",
      metaTitle: "Germany Land Values API (BORIS): keyless and free",
      h1: "Land values API for German cities (BORIS)",
      lead: "Official standard land values per city through a free, keyless REST API. The source is the BORIS geodata services of the federal states, aggregated to a building-land metric per city and delivered as consistent JSON.",
      dataDesc:
        "For each covered city the endpoint returns a building-land metric: median, minimum and maximum of standard land values in EUR per square meter, the number of zones and the reference date. Filtered to building land (residential, mixed, commercial) so forest and water zones do not distort the value.",
      sourceName: "BORIS (standard land value systems of the federal states)",
      sourceUrl: "https://www.bodenrichtwerte-boris.de/",
      license: "DL-DE Zero 2.0 or DL-DE BY 2.0 (per state)",
      licenseUrl: "https://www.govdata.de/dl-de/zero-2-0",
      vars: ["Median standard land value (EUR/m²)", "Minimum land value", "Maximum land value", "Number of land value zones", "Reference date"],
      keywords: ["land values API", "BORIS API", "standard land value Germany API", "property prices API", "building land API", "real estate data API Germany"],
      coverageNote: "Land values are available where the respective state provides an open BORIS service.",
      faq: [
        { q: "Is the land values API free and keyless?", a: "Yes. No key, no sign-up, free, a single GET request is enough. The rate limit is 300 requests per minute per IP." },
        { q: "What does the building-land metric mean?", a: "It is the median of a city's standard land values, filtered to building land (residential, mixed, commercial), plus minimum, maximum, zone count and reference date. This keeps the value meaningful and not distorted by forest or water areas." },
        { q: "Why is not every city covered?", a: "Standard land values are provided per federal state. Where a state offers no open BORIS service (for example license-restricted), the API answers honestly with not_covered instead of guessing." },
      ],
      datasetName: "InfraNode land values for German cities (BORIS)",
      datasetDesc: "Official standard land values as a building-land metric (median, minimum, maximum, zones, reference date) per city from state BORIS services, free and keyless via a JSON REST API.",
    },
  },
  {
    id: "solar",
    endpointId: "getCitySolar",
    examplePath: "/api/v1/cities/berlin/solar",
    coverageKey: "all",
    de: {
      slug: "solar-api",
      metaTitle: "Solar-API Deutschland (PVGIS): PV-Ertrag, keylos",
      h1: "Solar-API für deutsche Städte (PVGIS)",
      lead: "Solar-Potenzial je Stadt über eine kostenlose, keylose REST-API. Quelle ist PVGIS der Europäischen Kommission (JRC), aggregiert zu einer vergleichbaren Kennzahl je Stadt und einheitlich als JSON mit Quelle, Lizenz und Bezugszeitraum je Antwort.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt ein klimatologisches Mehrjahresmittel am Stadtzentrum, normiert auf eine 1-kWp-Anlage bei optimalem Neigungswinkel: Jahres-PV-Ertrag in kWh pro kWp, Globalstrahlung in kWh pro Quadratmeter, optimaler Neigungswinkel und Azimut sowie zwölf Monatswerte. Es ist kein Tageswert, sondern ein langjähriger Mittelwert; der Bezugszeitraum steht als Jahresspanne in der Antwort.",
      sourceName: "PVGIS, Europäische Kommission (JRC)",
      sourceUrl: "https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en",
      license: "EU-Wiederverwendungs-Policy (faktisch CC BY 4.0)",
      licenseUrl: "https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en",
      vars: ["Jahres-PV-Ertrag (kWh/kWp)", "Globalstrahlung (kWh/m²)", "Optimaler Neigungswinkel (Grad)", "Optimales Azimut (Grad, 0 = Süd)", "12 Monatswerte (Ertrag + Einstrahlung)", "Bezugszeitraum (Jahresspanne)"],
      keywords: ["Solar API Deutschland", "PVGIS API", "Solarpotenzial API", "Photovoltaik Ertrag API", "Globalstrahlung API", "PV Ertrag API kostenlos"],
      coverageNote: "Solar-Daten sind für alle 84 abgedeckten Städte verfügbar: PVGIS rechnet jede Koordinate in Europa, die Werte beziehen sich auf das Stadtzentrum.",
      faq: [
        { q: "Ist die Solar-API kostenlos und keylos?", a: "Ja. Kein Schlüssel, keine Anmeldung, kostenlos, ein GET-Request genügt. Das Rate-Limit beträgt 300 Anfragen pro Minute und IP." },
        { q: "Was bedeutet der Wert kWh pro kWp?", a: "Es ist der zu erwartende Jahresertrag einer Photovoltaikanlage je installiertem Kilowatt-Peak bei optimalem Neigungswinkel. So lassen sich Standorte direkt vergleichen und auf die geplante Anlagengröße hochrechnen." },
        { q: "Sind das aktuelle Messwerte?", a: "Nein. PVGIS liefert ein klimatologisches Mehrjahresmittel, also einen langjährigen Durchschnitt statt eines Tageswerts. Deshalb ist observed_at null; der Bezugszeitraum steht als Jahresspanne (period_start/period_end) in der Antwort." },
      ],
      datasetName: "InfraNode Solardaten deutscher Städte (PVGIS)",
      datasetDesc: "Solar-Einstrahlung und normierter PV-Ertrag (kWh/kWp, kWh/m², optimaler Winkel, Monatswerte) für 84 deutsche Städte aus PVGIS-Daten der Europäischen Kommission, kostenlos und keylos über eine REST-API als JSON.",
    },
    en: {
      slug: "solar-api",
      metaTitle: "Germany Solar API (PVGIS): PV yield, keyless",
      h1: "Solar API for German cities (PVGIS)",
      lead: "Solar potential per city through a free, keyless REST API. The source is PVGIS by the European Commission (JRC), aggregated to a comparable metric per city and delivered as consistent JSON with source, license and reference period on every response.",
      dataDesc:
        "For each city the endpoint returns a multi-year climatological average at the city centre, normalized to a 1 kWp system at the optimal tilt: annual PV yield in kWh per kWp, global irradiation in kWh per square meter, the optimal tilt and azimuth, and twelve monthly values. It is not a daily value but a long-term average; the reference period is given as a year range in the response.",
      sourceName: "PVGIS, European Commission (JRC)",
      sourceUrl: "https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en",
      license: "EU reuse policy (effectively CC BY 4.0)",
      licenseUrl: "https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en",
      vars: ["Annual PV yield (kWh/kWp)", "Global irradiation (kWh/m²)", "Optimal tilt (degrees)", "Optimal azimuth (degrees, 0 = south)", "12 monthly values (yield + irradiation)", "Reference period (year range)"],
      keywords: ["solar API Germany", "PVGIS API", "solar potential API", "photovoltaic yield API", "solar irradiation API", "free PV yield API"],
      coverageNote: "Solar data is available for all 84 covered cities: PVGIS computes any coordinate in Europe, the values refer to the city centre.",
      faq: [
        { q: "Is the solar API free and keyless?", a: "Yes. No key, no sign-up, free, a single GET request is enough. The rate limit is 300 requests per minute per IP." },
        { q: "What does kWh per kWp mean?", a: "It is the expected annual yield of a photovoltaic system per installed kilowatt-peak at the optimal tilt. This lets you compare locations directly and scale to your planned system size." },
        { q: "Are these live measurements?", a: "No. PVGIS provides a multi-year climatological average, a long-term mean rather than a daily value. That is why observed_at is null; the reference period is given as a year range (period_start/period_end) in the response." },
      ],
      datasetName: "InfraNode solar data for German cities (PVGIS)",
      datasetDesc: "Solar irradiation and normalized PV yield (kWh/kWp, kWh/m², optimal tilt, monthly values) for 84 German cities from European Commission PVGIS data, free and keyless via a JSON REST API.",
    },
  },
  {
    id: "solar-roofs",
    endpointId: "getCitySolarRoofs",
    examplePath: "/api/v1/cities/koeln/solar-roofs",
    coverageKey: "solar-roofs",
    de: {
      slug: "solarkataster-api",
      metaTitle: "Solarkataster-API: Dach-PV-Potenzial je Stadt, keylos",
      h1: "Solarkataster-API für deutsche Städte (Dach-PV)",
      lead: "Das Dach-Photovoltaik-Potenzial je Stadt über eine kostenlose, keylose REST-API. Quelle sind die amtlichen Solarkataster der Länder (NRW: LANUK/Geobasis NRW/MaStR; Bayern: Bayerisches Landesamt für Umwelt; Berlin: Umweltatlas/SenMVKU; Hamburg: LGV), je Gemeinde aggregiert und einheitlich als JSON mit Quelle und Lizenz je Antwort.",
      dataDesc:
        "Pro abgedeckter Stadt liefert der Endpunkt das gesamte installierbare Dach-PV-Potenzial (Leistung in kWp und Jahresertrag in MWh), den bereits installierten Bestand und den Ausschöpfungsgrad in Prozent; für NRW zusätzlich die Aufschlüsselung des Potenzials nach Gebäudekategorie. Je nach Quelle variiert der Umfang: Berlin enthält Potenzial und installierten Bestand, Hamburg derzeit nur das Potenzial. Anders als die Solar-API (Einstrahlung und Ertrag je kWp aus PVGIS) liefert diese Schnittstelle die Mengen je Stadt.",
      sourceName: "Solarkataster der Länder (NRW: LANUK/Geobasis NRW; Bayern: LfU; Berlin: Umweltatlas; Hamburg: LGV)",
      sourceUrl: "https://www.opengeodata.nrw.de/produkte/umwelt_klima/energie/solarkataster/",
      license: "DL-DE Zero 2.0 (NRW, Berlin), CC BY 4.0 (Bayern), DL-DE BY 2.0 (Hamburg)",
      licenseUrl: "https://www.govdata.de/dl-de/zero-2-0",
      vars: ["Installierbares Potenzial (kWp)", "Potenzieller Jahresertrag (MWh)", "Installierter Bestand (kWp)", "Ausschöpfungsgrad (%)", "Potenzial je Gebäudekategorie (NRW)", "Stichtag"],
      keywords: ["Solarkataster API", "Dach-PV Potenzial API", "Solarpotenzial API Deutschland", "Photovoltaik Dachflächen API", "PV Potenzial Stadt API", "Solarkataster NRW Bayern Berlin Hamburg Daten"],
      coverageNote: "Das Dach-Solarkataster ist pro Bundesland föderiert. Aktuell abgedeckt sind die Städte in Nordrhein-Westfalen und Bayern sowie die Stadtstaaten Berlin und Hamburg; weitere Länder folgen, sobald ihr offenes Gemeinde-Aggregat vorliegt.",
      faq: [
        { q: "Ist die Solarkataster-API kostenlos und keylos?", a: "Ja. Kein Schlüssel, keine Anmeldung, kostenlos, ein GET-Request genügt. Das Rate-Limit beträgt 300 Anfragen pro Minute und IP." },
        { q: "Worin unterscheidet sich diese API von der Solar-API?", a: "Die Solar-API (PVGIS) liefert die Sonneneinstrahlung und den erwartbaren Ertrag je installiertem Kilowatt-Peak für jede Stadt. Diese Solarkataster-API liefert das tatsächliche Dachpotenzial je Stadt: wie viel PV installierbar ist und wie viel davon bereits installiert ist." },
        { q: "Welche Länder sind abgedeckt?", a: "Aktuell Nordrhein-Westfalen (Solarkataster NRW, DL-DE Zero 2.0), Bayern (Energie-Atlas Bayern, CC BY 4.0), Berlin (Umweltatlas, DL-DE Zero 2.0) und Hamburg (Solarpotenzialanalyse, DL-DE BY 2.0). Dach-Solarkataster werden je Bundesland erhoben; weitere Länder kommen hinzu, sobald ein offenes Gemeinde-Aggregat vorliegt. Für Städte ohne abgedecktes Land antwortet die API ehrlich mit not_covered statt zu raten." },
      ],
      datasetName: "InfraNode Dach-Solarkataster (Potenzial je Stadt: NRW, Bayern, Berlin, Hamburg)",
      datasetDesc: "Installierbares und installiertes Dach-PV-Potenzial (kWp, MWh, Ausschöpfungsgrad) je Stadt aus den amtlichen Solarkatastern NRW, Bayern, Berlin und Hamburg, kostenlos und keylos über eine REST-API als JSON.",
    },
    en: {
      slug: "solar-cadastre-api",
      metaTitle: "Solar Cadastre API: rooftop PV potential, keyless",
      h1: "Solar cadastre API for German cities (rooftop PV)",
      lead: "Rooftop photovoltaic potential per city through a free, keyless REST API. The sources are the official state solar cadastres (NRW: LANUK/Geobasis NRW/MaStR; Bavaria: Bavarian Environment Agency; Berlin: Umweltatlas/SenMVKU; Hamburg: LGV), aggregated per municipality and delivered as consistent JSON with source and license on every response.",
      dataDesc:
        "For each covered city the endpoint returns the total installable rooftop PV potential (capacity in kWp and annual yield in MWh), the already installed stock and the exploitation ratio in percent; for NRW also the potential broken down per building category. Coverage varies by source: Berlin includes potential and installed stock, Hamburg currently only the potential. Unlike the solar API (irradiation and yield per kWp from PVGIS), this interface returns the per-city quantities.",
      sourceName: "State solar cadastres (NRW: LANUK/Geobasis NRW; Bavaria: LfU; Berlin: Umweltatlas; Hamburg: LGV)",
      sourceUrl: "https://www.opengeodata.nrw.de/produkte/umwelt_klima/energie/solarkataster/",
      license: "DL-DE Zero 2.0 (NRW, Berlin), CC BY 4.0 (Bavaria), DL-DE BY 2.0 (Hamburg)",
      licenseUrl: "https://www.govdata.de/dl-de/zero-2-0",
      vars: ["Installable potential (kWp)", "Potential annual yield (MWh)", "Installed stock (kWp)", "Exploitation ratio (%)", "Potential per building category (NRW)", "Reference date"],
      keywords: ["solar cadastre API", "rooftop PV potential API", "solar potential API Germany", "photovoltaic rooftop API", "PV potential city API", "Solarkataster NRW Bavaria Berlin Hamburg data"],
      coverageNote: "The rooftop solar cadastre is federated per federal state. Currently covered are the cities in North Rhine-Westphalia and Bavaria as well as the city states Berlin and Hamburg; more states follow once their open municipal aggregate is available.",
      faq: [
        { q: "Is the solar cadastre API free and keyless?", a: "Yes. No key, no sign-up, free, a single GET request is enough. The rate limit is 300 requests per minute per IP." },
        { q: "How does this differ from the solar API?", a: "The solar API (PVGIS) returns solar irradiation and the expected yield per installed kilowatt-peak for any city. This solar cadastre API returns the actual rooftop potential per city: how much PV is installable and how much is already installed." },
        { q: "Which states are covered?", a: "Currently North Rhine-Westphalia (Solarkataster NRW, DL-DE Zero 2.0), Bavaria (Energie-Atlas Bayern, CC BY 4.0), Berlin (Umweltatlas, DL-DE Zero 2.0) and Hamburg (solar potential analysis, DL-DE BY 2.0). Rooftop solar cadastres are compiled per federal state; more states are added once an open municipal aggregate is available. For cities without a covered state the API answers honestly with not_covered instead of guessing." },
      ],
      datasetName: "InfraNode rooftop solar cadastre (potential per city: NRW, Bavaria, Berlin, Hamburg)",
      datasetDesc: "Installable and installed rooftop PV potential (kWp, MWh, exploitation ratio) per city from the official NRW, Bavaria, Berlin and Hamburg solar cadastres, free and keyless via a JSON REST API.",
    },
  },
  {
    id: "public-transport",
    endpointId: "getCityStationDepartures",
    examplePath: "/api/v1/cities/berlin/station-departures",
    // ÖPNV-Echtzeit gibt es für alle Städte (DELFI/HVV GTFS), daher "all".
    // Vorher fälschlich "station-departures" (kein Key in coverage.json) ->
    // Topic erschien auf KEINER Stadt-Landingpage. Fix 2026-06-23.
    coverageKey: "all",
    de: {
      slug: "oepnv-echtzeit-api",
      metaTitle: "ÖPNV-Echtzeit-API Deutschland: Abfahrten, keylos",
      h1: "ÖPNV-Echtzeit-API für deutsche Städte",
      lead: "Echtzeit-Abfahrten an Haltestellen deutscher Großstädte über eine kostenlose, keylose REST-API. Datengrundlage sind DELFI und GTFS sowie regionale Verkehrsverbünde, einheitlich als JSON mit Quelle und Zeitstempel je Antwort.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt die nächsten Abfahrten an einer zentralen Haltestelle: Linie, Richtung, geplante und prognostizierte Abfahrtszeit sowie Verspätung. Ein paralleler Endpunkt liefert analog die Ankünfte.",
      sourceName: "DELFI, GTFS und regionale Verkehrsverbünde",
      sourceUrl: "https://www.delfi.de/",
      license: "CC BY 4.0 bzw. verbundspezifisch",
      licenseUrl: "https://creativecommons.org/licenses/by/4.0/",
      vars: ["Linie", "Richtung und Ziel", "Geplante Abfahrtszeit", "Prognostizierte Abfahrtszeit", "Verspätung", "Haltestelle"],
      keywords: ["ÖPNV API Deutschland", "Abfahrten API", "Echtzeit ÖPNV API", "GTFS Echtzeit API", "Fahrplan API kostenlos", "public transport API Germany"],
      coverageNote: "Echtzeit-Abfahrten sind für die Städte mit angebundenen Verbund- bzw. DELFI-Daten verfügbar.",
      faq: [
        { q: "Ist die ÖPNV-Echtzeit-API kostenlos und keylos?", a: "Ja. Kein Schlüssel, keine Anmeldung, kostenlos, ein GET-Request genügt. Das Rate-Limit beträgt 300 Anfragen pro Minute und IP." },
        { q: "Welche Daten enthält eine Abfahrt?", a: "Linie, Richtung und Ziel, die geplante und die prognostizierte Abfahrtszeit sowie die Verspätung, jeweils an einer zentralen Haltestelle der Stadt." },
        { q: "Welche Quellen stehen dahinter?", a: "DELFI und GTFS sowie regionale Verkehrsverbünde. Die jeweils gültige Lizenz und der Attributionshinweis stehen in jeder API-Antwort." },
      ],
      datasetName: "InfraNode ÖPNV-Echtzeit-Abfahrten deutscher Städte",
      datasetDesc: "Echtzeit-Abfahrten und -Ankünfte an Haltestellen deutscher Großstädte aus DELFI-, GTFS- und Verbunddaten, kostenlos und keylos über eine REST-API als JSON.",
    },
    en: {
      slug: "public-transport-api",
      metaTitle: "Public Transport API Germany: real-time, keyless",
      h1: "Real-time public transport API for German cities",
      lead: "Real-time departures at stops in major German cities through a free, keyless REST API. The data is based on DELFI and GTFS plus regional transit associations, delivered as consistent JSON with source and timestamp on every response.",
      dataDesc:
        "For each city the endpoint returns the next departures at a central stop: line, direction, planned and predicted departure time and delay. A parallel endpoint returns arrivals in the same shape.",
      sourceName: "DELFI, GTFS and regional transit associations",
      sourceUrl: "https://www.delfi.de/",
      license: "CC BY 4.0 or association-specific",
      licenseUrl: "https://creativecommons.org/licenses/by/4.0/",
      vars: ["Line", "Direction and destination", "Planned departure time", "Predicted departure time", "Delay", "Stop"],
      keywords: ["public transport API Germany", "departures API", "real-time transit API", "GTFS realtime API", "free timetable API", "German transit API"],
      coverageNote: "Real-time departures are available for cities with connected association or DELFI data.",
      faq: [
        { q: "Is the public transport API free and keyless?", a: "Yes. No key, no sign-up, free, a single GET request is enough. The rate limit is 300 requests per minute per IP." },
        { q: "What data does a departure contain?", a: "Line, direction and destination, the planned and predicted departure time and the delay, at a central stop in the city." },
        { q: "Which sources are behind it?", a: "DELFI and GTFS plus regional transit associations. The applicable license and attribution note are included in every API response." },
      ],
      datasetName: "InfraNode real-time public transport departures for German cities",
      datasetDesc: "Real-time departures and arrivals at stops in major German cities from DELFI, GTFS and transit association data, free and keyless via a JSON REST API.",
    },
  },
  {
    id: "public-tenders",
    endpointId: "getCityPublicTenders",
    examplePath: "/api/v1/cities/koeln/public-tenders",
    // Bundesweite OCDS-Quelle (Datenservice Öffentlicher Einkauf), daher "all".
    coverageKey: "all",
    de: {
      slug: "vergabe-api",
      metaTitle: "Vergabe-API Deutschland: öffentliche Aufträge, keylos",
      h1: "API für öffentliche Auftragsvergabe deutscher Städte",
      lead: "Laufende Ausschreibungen und vergebene Aufträge deutscher Städte über eine kostenlose, keylose REST-API. Quelle ist der Datenservice Öffentlicher Einkauf (oeffentlichevergabe.de) im OCDS-Standard, einheitlich als JSON mit Quelle, Lizenz und Zeitstempel je Antwort.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt die öffentlichen Vergabebekanntmachungen: Bekanntmachungstyp (Ausschreibung oder Zuschlag), Status, Auftraggeber-Ort, Region (NUTS), Leistungsgegenstand (CPV) und, soweit veröffentlicht, der Auftragswert. Bei vergebenen Aufträgen kommen die Auftragnehmer (Feld suppliers, Namensliste) und der tatsächlich vergebene Auftragswert (award_value/award_currency) dazu, soweit die Vergabestelle sie im amtlichen Export offenlegt. Filtern lässt sich nach Status (active für laufende, complete für vergebene Aufträge).",
      sourceName: "Datenservice Öffentlicher Einkauf",
      sourceUrl: "https://www.oeffentlichevergabe.de/",
      license: "CC0",
      licenseUrl: "https://creativecommons.org/publicdomain/zero/1.0/",
      vars: ["Bekanntmachungstyp (Ausschreibung/Zuschlag)", "Status", "Auftraggeber-Ort", "Region (NUTS)", "Leistungsgegenstand (CPV)", "Auftragswert", "Auftragnehmer (suppliers)", "Zuschlagswert (award_value)"],
      keywords: ["Vergabe API Deutschland", "öffentliche Aufträge API", "Ausschreibungen API", "OCDS API Deutschland", "Auftragsvergabe Daten API", "public procurement API Germany"],
      coverageNote: "Die Abdeckung wächst: Oberschwellige Bekanntmachungen sind vollständig, unterschwellige werden ab 2024 schrittweise ergänzt.",
      faq: [
        { q: "Ist die Vergabe-API kostenlos und ohne Schlüssel nutzbar?", a: "Ja. Die API ist keylos und kostenlos, ein GET-Request ohne Anmeldung genügt. Das Rate-Limit beträgt 300 Anfragen pro Minute und IP." },
        { q: "Welche Vergabedaten sind enthalten?", a: "Laufende Ausschreibungen und bereits vergebene Aufträge je Stadt mit Bekanntmachungstyp, Status, Auftraggeber-Ort, Region (NUTS), Leistungsgegenstand (CPV) und, soweit veröffentlicht, dem Auftragswert. Bei Zuschlägen zusätzlich die Auftragnehmer (suppliers) und der vergebene Auftragswert (award_value)." },
        { q: "Sind die Auftragnehmer (Zuschlagsempfänger) enthalten?", a: "Ja. Bei vergebenen Aufträgen liefert das Feld suppliers die Namen der Auftragnehmer, aktuell bei über 80 Prozent der Zuschläge. Eine leere Liste bedeutet: Die Vergabestelle hat den Auftragnehmer nicht maschinenlesbar veröffentlicht." },
        { q: "Warum fehlen manche Werte oder wirken ungewöhnlich?", a: "InfraNode liefert die Daten quellentreu aus dem amtlichen OCDS-Export. Beträge kleiner oder gleich 0 werden als nicht angegeben (null) gewertet; andere Eintragungen der Vergabestellen, auch symbolische Kleinstbeträge, bleiben unverändert erhalten. Die Angebotsfrist (deadline) enthält der Export grundsätzlich nicht, sie steht nur in der Original-Bekanntmachung über source_url." },
        { q: "Welche Lizenz gilt für die Vergabedaten?", a: "Die Daten stammen aus dem Datenservice Öffentlicher Einkauf und werden unter CC0 durchgereicht. Lizenz-URL und Attribution stehen in jeder API-Antwort im attribution-Block." },
      ],
      datasetName: "InfraNode Vergabedaten deutscher Städte (Datenservice Öffentlicher Einkauf)",
      datasetDesc: "Laufende Ausschreibungen und vergebene Aufträge deutscher Städte aus dem Datenservice Öffentlicher Einkauf (OCDS, CC0), kostenlos und keylos über eine REST-API als JSON.",
    },
    en: {
      slug: "public-procurement-api",
      metaTitle: "Germany Public Procurement API: tenders, keyless",
      h1: "Public procurement API for German cities",
      lead: "Running tenders and awarded contracts for German cities through a free, keyless REST API. The source is the German public procurement data service (oeffentlichevergabe.de) in the OCDS standard, delivered as consistent JSON with source, license and timestamp on every response.",
      dataDesc:
        "For each city the endpoint returns public procurement notices: notice type (tender or award), status, buyer city, region (NUTS), subject of the contract (CPV) and, where published, the contract value. Awarded contracts additionally carry the contractors (suppliers field, list of names) and the actually awarded value (award_value/award_currency), where the contracting authority discloses them in the official export. Results can be filtered by status (active for running tenders, complete for awarded contracts).",
      sourceName: "German public procurement data service",
      sourceUrl: "https://www.oeffentlichevergabe.de/",
      license: "CC0",
      licenseUrl: "https://creativecommons.org/publicdomain/zero/1.0/",
      vars: ["Notice type (tender/award)", "Status", "Buyer city", "Region (NUTS)", "Contract subject (CPV)", "Contract value", "Contractors (suppliers)", "Awarded value (award_value)"],
      keywords: ["public procurement API Germany", "public tenders API", "tenders API Germany", "OCDS API Germany", "procurement data API", "government contracts API Germany"],
      coverageNote: "Coverage is growing: above-threshold notices are complete, below-threshold notices are added gradually from 2024 onward.",
      faq: [
        { q: "Is the public procurement API free and usable without a key?", a: "Yes. The API is keyless and free; a GET request without sign-up is enough. The rate limit is 300 requests per minute per IP." },
        { q: "Which procurement data is included?", a: "Running tenders and already awarded contracts per city with notice type, status, buyer city, region (NUTS), contract subject (CPV) and, where published, the contract value. Awards additionally carry the contractors (suppliers) and the awarded value (award_value)." },
        { q: "Are the contractors (award winners) included?", a: "Yes. For awarded contracts the suppliers field lists the contractor names, currently for more than 80 percent of awards. An empty list means the contracting authority did not publish the contractor in machine-readable form." },
        { q: "Why are some values missing or unusual?", a: "InfraNode delivers the data faithfully from the official OCDS export. Amounts of 0 or less are treated as not stated (null); other entries by contracting authorities, including symbolic minimal amounts, remain unchanged. The submission deadline is not part of the export at all and is only found in the original notice via source_url." },
        { q: "Which license applies to the procurement data?", a: "Data comes from the German public procurement data service and is passed through under CC0. The license URL and attribution are included in every API response in the attribution block." },
      ],
      datasetName: "InfraNode public procurement data for German cities (German procurement data service)",
      datasetDesc: "Running tenders and awarded contracts for German cities from the German public procurement data service (OCDS, CC0), free and keyless via a JSON REST API.",
    },
  },
  {
    id: "council-papers",
    endpointId: "getCityCouncilPapers",
    examplePath: "/api/v1/cities/dresden/council-papers",
    coverageKey: "council-papers",
    de: {
      slug: "ratsinformationen-api",
      metaTitle: "Ratsinformationen-API: Beschlüsse, OParl, keylos",
      h1: "API für kommunale Ratsinformationen deutscher Städte",
      lead: "Vorlagen, Anträge und Beschlüsse der Stadträte über eine kostenlose, keylose REST-API. Quelle sind die kommunalen Ratsinformationssysteme im OParl-Standard, einheitlich als JSON mit Quelle, Lizenz und Zeitstempel je Antwort. Was die Stadt entscheidet, analog zu was die Stadt einkauft (Vergabe-API).",
      dataDesc:
        "Pro Stadt liefert der Endpunkt die kommunalen Ratsinformationen (OParl \"Paper\"): Titel, Aktenzeichen (Referenz), Datum, Paper-Typ (Vorlage, Antrag, Beschluss) und den Link zur Hauptdatei. Das PDF selbst wird nicht gespiegelt, nur der Original-Link durchgereicht. Filtern lässt sich nach Stichwort, Paper-Typ und Datum.",
      sourceName: "Kommunale Ratsinformationssysteme (OParl)",
      sourceUrl: "https://oparl.org/",
      license: "DL-DE/Zero, DL-DE/BY, CC BY (je Stadt)",
      licenseUrl: "https://www.govdata.de/dl-de/zero-2-0",
      vars: ["Titel", "Referenz (Aktenzeichen)", "Datum", "Paper-Typ", "Link zur Hauptdatei"],
      keywords: ["Ratsinformationen API", "OParl API Deutschland", "kommunale Beschlüsse API", "Ratsinformationssystem API", "Vorlagen Anträge Beschlüsse API", "council information API Germany"],
      coverageNote: "Abgedeckt sind acht lizenzgeklärte Städte: Dresden, Köln, Düsseldorf, Münster, Leipzig, Magdeburg, Osnabrück und Freiburg im Breisgau. Die Abdeckung wächst mit jeder weiteren lizenzgeklärten Stadt.",
      faq: [
        { q: "Ist die Ratsinformationen-API kostenlos und ohne Schlüssel nutzbar?", a: "Ja. Die API ist keylos und kostenlos, ein GET-Request ohne Anmeldung genügt. Das Rate-Limit beträgt 300 Anfragen pro Minute und IP." },
        { q: "Welche Städte sind enthalten?", a: "Aktuell acht lizenzgeklärte Städte: Dresden, Köln, Düsseldorf, Münster, Leipzig, Magdeburg, Osnabrück und Freiburg im Breisgau. Nicht abgedeckte Städte liefern einen 404 mit Hinweis." },
        { q: "Welche Lizenz gilt für die Ratsinformationen?", a: "Je Stadt eine eigene Lizenz (DL-DE/Zero 2.0 für Dresden/Köln/Düsseldorf, DL-DE/BY 2.0 für Münster, CC BY 4.0 für Leipzig). Lizenz-URL und Attribution stehen in jeder API-Antwort im attribution-Block." },
      ],
      datasetName: "InfraNode Ratsinformationen deutscher Städte (OParl)",
      datasetDesc: "Kommunale Vorlagen, Anträge und Beschlüsse deutscher Städte aus den Ratsinformationssystemen im OParl-Standard, kostenlos und keylos über eine REST-API als JSON.",
    },
    en: {
      slug: "council-information-api",
      metaTitle: "Germany Council Information API: OParl, keyless",
      h1: "Council information API for German cities",
      lead: "Council papers, motions and resolutions of German city councils through a free, keyless REST API. The source is the municipal council information systems in the OParl standard, delivered as consistent JSON with source, license and timestamp on every response. What the city decides, alongside what the city buys (procurement API).",
      dataDesc:
        "For each city the endpoint returns municipal council information (OParl \"Paper\"): title, reference, date, paper type (paper, motion, resolution) and a link to the main file. The PDF itself is not mirrored, only the original link is passed through. Results can be filtered by keyword, paper type and date.",
      sourceName: "Municipal council information systems (OParl)",
      sourceUrl: "https://oparl.org/",
      license: "DL-DE/Zero, DL-DE/BY, CC BY (per city)",
      licenseUrl: "https://www.govdata.de/dl-de/zero-2-0",
      vars: ["Title", "Reference", "Date", "Paper type", "Link to main file"],
      keywords: ["council information API Germany", "OParl API Germany", "municipal resolutions API", "council papers API", "city council API Germany", "Ratsinformationen API"],
      coverageNote: "Covered are eight licence-cleared cities: Dresden, Cologne, Düsseldorf, Münster, Leipzig, Magdeburg, Osnabrück and Freiburg im Breisgau. Coverage grows with every further licence-cleared city.",
      faq: [
        { q: "Is the council information API free and usable without a key?", a: "Yes. The API is keyless and free; a GET request without sign-up is enough. The rate limit is 300 requests per minute per IP." },
        { q: "Which cities are included?", a: "Currently eight licence-cleared cities: Dresden, Cologne, Düsseldorf, Münster, Leipzig, Magdeburg, Osnabrück and Freiburg im Breisgau. Cities not covered return a 404 with a hint." },
        { q: "Which license applies to the council information?", a: "Each city has its own license (DL-DE/Zero 2.0 for Dresden/Cologne/Düsseldorf, DL-DE/BY 2.0 for Münster, CC BY 4.0 for Leipzig). The license URL and attribution are included in every API response in the attribution block." },
      ],
      datasetName: "InfraNode council information for German cities (OParl)",
      datasetDesc: "Municipal council papers, motions and resolutions for German cities from council information systems in the OParl standard, free and keyless via a JSON REST API.",
    },
  },
  {
    id: "tax-rates",
    endpointId: "getCityTaxRates",
    examplePath: "/api/v1/cities/koeln/tax-rates",
    coverageKey: "all",
    de: {
      slug: "hebesaetze-api",
      metaTitle: "Hebesatz-API Deutschland, Realsteuern keylos",
      h1: "Hebesatz-API für deutsche Städte (Realsteuern)",
      lead: "Der Gewerbesteuer-Hebesatz entscheidet mit darüber, was ein Standort kostet, und er ist von Stadt zu Stadt verschieden. Diese API gibt ihn für jede Stadt im Register heraus, dazu die Grundsteuersätze und den Stichtag, auf den sich alles bezieht. Gemeindegenau aus der Regionaldatenbank Deutschland, ohne Schlüssel und ohne Anmeldung.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt den Gewerbesteuer-Hebesatz sowie die Grundsteuer-Hebesätze A und B, dazu Grundsteuer C, wo die Gemeinde sie beschlossen hat, und den Stichtag, auf den sich die Sätze beziehen. Alle Werte sind Prozentsätze im Sinne des Hebesatzrechts, unverändert aus der amtlichen Meldung.",
      sourceName: "Statistische Ämter des Bundes und der Länder, Regionaldatenbank Deutschland",
      sourceUrl: "https://www.regionalstatistik.de/",
      license: "DL-DE/BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Gewerbesteuer-Hebesatz", "Grundsteuer-Hebesatz A (Betriebe der Landwirtschaft)", "Grundsteuer-Hebesatz B (übrige Grundstücke)", "Grundsteuer-Hebesatz C (wo erhoben)", "Stichtag der Hebesätze"],
      keywords: ["Hebesatz API", "Gewerbesteuer Hebesatz Daten", "Grundsteuer Hebesatz Liste", "Realsteuern Open Data", "Hebesatz API Deutschland"],
      coverageNote: "Alle Städte im Register. Die Hebesätze sind gemeindegenau gemeldet, sie gelten also exakt für das Stadtgebiet und nicht für einen umgebenden Kreis. Grundsteuer C führen nur Gemeinden, die den gesonderten Satz für baureife Grundstücke beschlossen haben, sonst steht dort null.",
      faq: [
        {
          q: "Was bedeutet der Hebesatz genau?",
          a: "Der Hebesatz ist der Prozentsatz, mit dem die Gemeinde den bundesrechtlich ermittelten Steuermessbetrag multipliziert. Bei einem Gewerbesteuer-Hebesatz von 475 Prozent und einem Messbetrag von 1.000 Euro ergibt das 4.750 Euro Steuer.",
        },
        {
          q: "Warum steht bei Grundsteuer C oft null?",
          a: "Grundsteuer C ist ein gesonderter, meist höherer Satz für baureife unbebaute Grundstücke und für die Gemeinde freiwillig. Wo sie nicht beschlossen wurde, meldet die Antwort null, statt einen Wert zu erfinden.",
        },
        {
          q: "Wie aktuell sind die Sätze?",
          a: "Jede Antwort trägt den Stichtag der amtlichen Meldung. Hebesätze ändern sich in der Regel zum Jahreswechsel, deshalb ist der Stichtag die wichtigere Angabe als der Abrufzeitpunkt.",
        },
        {
          q: "Sind Grundsteuersätze über Jahre hinweg vergleichbar?",
          a: "Nur eingeschränkt. Mit der Grundsteuerreform ab dem Steuerjahr 2025 hat sich die Bemessungsgrundlage geändert, viele Gemeinden haben ihren Hebesatz deshalb angepasst, ohne die Steuerlast im gleichen Maß zu verändern. Ein reiner Satzvergleich mit früheren Jahren führt in die Irre.",
        },
      ],
      datasetName: "Realsteuer-Hebesätze je deutscher Stadt",
      datasetDesc: "Gewerbesteuer- und Grundsteuer-Hebesätze je Stadt mit Stichtag aus der Regionaldatenbank Deutschland.",
    },
    en: {
      slug: "tax-rates-api",
      metaTitle: "Municipal tax rate API Germany, key-free",
      h1: "Municipal tax rate API for German cities",
      lead: "The trade tax multiplier is part of what a location costs, and it differs from city to city. This API returns it for every city in the register, together with the property tax rates and the date they apply to. Reported per municipality by the German federal and state statistical offices, no key and no sign-up.",
      dataDesc:
        "Per city the endpoint returns the trade tax multiplier and the property tax multipliers A and B, plus property tax C where the municipality has adopted it, and the reference date the rates apply to. All values are the official percentages, passed through unchanged.",
      sourceName: "German federal and state statistical offices, regional database Germany",
      sourceUrl: "https://www.regionalstatistik.de/",
      license: "DL-DE/BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Trade tax multiplier", "Property tax multiplier A (agricultural holdings)", "Property tax multiplier B (other properties)", "Property tax multiplier C (where levied)", "Reference date of the rates"],
      keywords: ["municipal tax rate API", "trade tax multiplier data", "property tax Germany API", "Hebesatz API", "local tax open data"],
      coverageNote: "All cities in the register. The multipliers are reported per municipality, so they apply exactly to the city and not to a surrounding district. Property tax C exists only where the municipality adopted the separate rate for building-ready land, otherwise the field is null.",
      faq: [
        {
          q: "What exactly is a tax multiplier?",
          a: "It is the percentage the municipality applies to the tax base amount set by federal law. A trade tax multiplier of 475 percent on a base amount of 1,000 euros results in 4,750 euros of tax.",
        },
        {
          q: "Why is property tax C often null?",
          a: "Property tax C is a separate, usually higher rate for building-ready undeveloped land and is optional for the municipality. Where it was not adopted, the response returns null instead of inventing a value.",
        },
        {
          q: "How current are the rates?",
          a: "Every response carries the reference date of the official report. Multipliers usually change at the turn of the year, which makes the reference date more meaningful than the retrieval time.",
        },
        {
          q: "Are property tax rates comparable across years?",
          a: "Only to a limited extent. The German property tax reform changed the assessment base from the 2025 tax year, and many municipalities adjusted their multiplier without changing the actual tax burden by the same amount. Comparing rates alone is misleading.",
        },
      ],
      datasetName: "Municipal tax multipliers per German city",
      datasetDesc: "Trade tax and property tax multipliers per city with reference date from the regional database Germany.",
    },
  },
  {
    id: "demographics",
    endpointId: "getCityDemographics",
    examplePath: "/api/v1/cities/koeln/demographics",
    coverageKey: "all",
    de: {
      slug: "einwohnerzahlen-api",
      metaTitle: "Einwohnerzahlen-API Deutschland, keylos",
      h1: "Einwohnerzahl- und Dichte-API für deutsche Städte",
      lead: "Eine Stadt kann viele Einwohner haben und trotzdem locker bebaut sein. Deshalb liefert diese API beides: die Einwohnerzahl aus Wikidata und die Dichte, exakt je Stadt aus dem 100-Meter-Gitter des Zensus 2022 gerechnet. Beide Werte kommen keylos und immer mit dem Jahr, auf das sie sich beziehen.",
      dataDesc:
        "Ein Endpunkt liefert die Einwohnerzahl mit Berichtsjahr, dazu Haushalte, Gebäudebestand und Durchschnittsmiete, soweit für die Stadt gemeldet. Ein zweiter Endpunkt liefert die Einwohnerdichte: die Summe der Einwohner über alle bewohnten Gitterzellen der Stadt, die Anzahl dieser Zellen, die daraus folgende bewohnte Fläche in Quadratkilometern und die Dichte je Quadratkilometer. Bezugsgröße der Dichte ist die bewohnte Fläche, nicht die Gesamtfläche der Stadt.",
      sourceName: "Wikidata (Einwohnerzahl) und Zensus 2022, Statistische Ämter des Bundes und der Länder (Dichte)",
      sourceUrl: "https://www.zensus2022.de/",
      license: "CC0 1.0 (Wikidata) und DL-DE/BY 2.0 (Zensus 2022)",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Einwohnerzahl", "Berichtsjahr", "Haushalte (wo gemeldet)", "Gebäudebestand (wo gemeldet)", "Durchschnittsmiete (wo gemeldet)", "Einwohnerdichte je Quadratkilometer", "Bewohnte 100-Meter-Zellen", "Bewohnte Fläche in Quadratkilometern", "Berichtsjahr des Zensus"],
      coverageNote: "Alle Städte im Register. Die Dichte wird je amtlichem Gemeindeschlüssel server-seitig aus dem Zensus-Gitter aggregiert, ohne Massendownload. Haushalte, Gebäude und Miete sind nur dort gefüllt, wo sie gemeldet sind, sonst steht null.",
      keywords: ["Einwohnerzahl API", "Bevoelkerungsdichte Daten", "Zensus 2022 API", "Einwohner Deutschland API", "Bevoelkerung Open Data"],
      faq: [
        {
          q: "Warum weicht die Einwohnerzahl von der Zensus-Summe ab?",
          a: "Es sind zwei verschiedene Größen. Die Einwohnerzahl ist die fortgeschriebene Zahl aus Wikidata, die Zensus-Summe zählt die Einwohner in den bewohnten Gitterzellen zum Stichtag 2022. Beide Werte stehen mit ihrem Bezugsjahr in der Antwort, damit die Differenz erklärbar bleibt und nicht als Fehler erscheint.",
        },
        {
          q: "Auf welche Fläche bezieht sich die Dichte?",
          a: "Auf die bewohnte Fläche, also die Zahl der bewohnten 100-Meter-Zellen mal 0,01 Quadratkilometer. Das ergibt eine höhere Dichte als der Bezug auf die Gesamtfläche, beschreibt aber die tatsächlich besiedelte Stadt. Beide Zwischenwerte liefert die Antwort mit, sodass sich jede andere Bezugsgröße selbst rechnen lässt.",
        },
        {
          q: "Welche Lizenz gilt für welche Zahl?",
          a: "Die Einwohnerzahl aus Wikidata steht unter CC0 1.0, die Zensus-Dichte unter DL-DE/BY 2.0 mit Namensnennung der Statistischen Ämter des Bundes und der Länder. Jede Antwort trägt ihre Lizenz und die verbindliche Attribution im eigenen Block.",
        },
        {
          q: "Gibt es die Werte auch je Stadtteil?",
          a: "Nein. Die Aggregation erfolgt je Stadt über den Gemeindeschlüssel. Feinere Zuschnitte würden eine eigene Gebietsabgrenzung erfordern, die die Quelle nicht mitliefert.",
        },
      ],
      datasetName: "Einwohnerzahl und Einwohnerdichte je deutscher Stadt",
      datasetDesc: "Einwohnerzahl je Stadt aus Wikidata und exakt aggregierte Einwohnerdichte aus dem 100-Meter-Gitter des Zensus 2022.",
    },
    en: {
      slug: "population-api",
      metaTitle: "Population API Germany, key-free",
      h1: "Population and density API for German cities",
      lead: "A city can have a large population and still be loosely built up. That is why this API returns both: the population figure from Wikidata and the density, computed exactly per city from the 100 metre grid of the 2022 German census. Both values come key-free and always with the year they refer to.",
      dataDesc:
        "One endpoint returns the population with its reference year, plus households, building stock and average rent where reported for the city. A second endpoint returns the population density: the sum of inhabitants across all populated grid cells of the city, the number of those cells, the resulting populated area in square kilometres and the density per square kilometre. The density refers to the populated area, not to the total area of the city.",
      sourceName: "Wikidata (population) and 2022 census, German federal and state statistical offices (density)",
      sourceUrl: "https://www.zensus2022.de/",
      license: "CC0 1.0 (Wikidata) and DL-DE/BY 2.0 (2022 census)",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Population", "Reference year", "Households (where reported)", "Building stock (where reported)", "Average rent (where reported)", "Population density per square kilometre", "Populated 100 metre cells", "Populated area in square kilometres", "Census reference year"],
      coverageNote: "All cities in the register. The density is aggregated server-side per official municipality key from the census grid, without a bulk download. Households, buildings and rent are only filled where they are reported, otherwise the field is null.",
      keywords: ["population API Germany", "population density data", "census 2022 API", "German city population API", "population open data"],
      faq: [
        {
          q: "Why does the population differ from the census sum?",
          a: "They are two different figures. The population is the projected number from Wikidata, the census sum counts inhabitants in populated grid cells as of 2022. Both values carry their reference year in the response, so the difference stays explainable instead of looking like an error.",
        },
        {
          q: "Which area is the density based on?",
          a: "On the populated area, that is the number of populated 100 metre cells times 0.01 square kilometres. This yields a higher density than using the total area, but it describes the actually settled city. Both intermediate values are included, so any other reference area can be computed.",
        },
        {
          q: "Which licence applies to which figure?",
          a: "The Wikidata population is CC0 1.0, the census density is DL-DE/BY 2.0 requiring attribution of the German federal and state statistical offices. Every response carries its licence and the binding attribution in a dedicated block.",
        },
        {
          q: "Are the values available per district?",
          a: "No. The aggregation runs per city via the municipality key. Finer cuts would require a boundary definition the source does not provide.",
        },
      ],
      datasetName: "Population and density per German city",
      datasetDesc: "Population per city from Wikidata and exactly aggregated population density from the 100 metre grid of the 2022 German census.",
    },
  },
  {
    id: "crime-stats",
    endpointId: "getCityCrimeStats",
    examplePath: "/api/v1/cities/koeln/crime-stats",
    coverageKey: "all",
    de: {
      slug: "kriminalstatistik-api",
      metaTitle: "Kriminalstatistik-API Deutschland (PKS)",
      h1: "PKS-API für deutsche Städte (Kriminalstatistik)",
      lead: "Eine nackte Fallzahl sagt wenig, solange die Einwohnerzahl daneben fehlt. Diese API liefert deshalb zu jeder Hauptstraftatengruppe drei Zahlen: Fälle, Häufigkeitszahl je 100.000 Einwohner und Aufklärungsquote, direkt aus der Polizeilichen Kriminalstatistik des Bundeskriminalamts. Keylos abrufbar, mit Berichtsjahr und Version in jeder Antwort.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt das Berichtsjahr, die Version der Statistik und je Hauptstraftatengruppe die Fallzahl, die Häufigkeitszahl je 100.000 Einwohner und die Aufklärungsquote in Prozent. Die Gruppe Straftaten insgesamt ist enthalten, Gesamtwert und Teilgruppen stehen also in derselben Antwort.",
      sourceName: "Polizeiliche Kriminalstatistik (PKS) - Bundeskriminalamt",
      sourceUrl: "https://www.bka.de/DE/AktuelleInformationen/StatistikenLagebilder/PolizeilicheKriminalstatistik/pks_node.html",
      license: "DL-DE/BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Berichtsjahr", "Version der Statistik", "Hauptstraftatengruppe mit Bezeichnung", "Fallzahl", "Häufigkeitszahl je 100.000 Einwohner", "Aufklärungsquote in Prozent"],
      keywords: ["PKS API", "Kriminalstatistik API", "Kriminalitaet Daten Deutschland", "Haeufigkeitszahl Kreis", "Aufklaerungsquote Open Data"],
      coverageNote: "Alle Städte im Register. Die PKS liegt je Kreis und kreisfreier Stadt vor: bildet eine Stadt keinen eigenen Kreis, gilt der Wert für den umgebenden Kreis und nicht für die Stadtgrenze. Berichtsjahr und Version stehen in jeder Antwort, weil das Bundeskriminalamt beides zur Attribution verlangt.",
      faq: [
        {
          q: "Was ist die Häufigkeitszahl?",
          a: "Die Zahl der Fälle je 100.000 Einwohner. Sie macht Regionen unterschiedlicher Größe vergleichbar, während die reine Fallzahl vor allem die Einwohnerzahl widerspiegelt.",
        },
        {
          q: "Gilt der Wert für die Stadt oder für den Kreis?",
          a: "Für die kreisfreie Stadt gilt er stadtgenau. Liegt die Stadt in einem Landkreis, ist der gemeldete Wert der Kreiswert, weil die PKS nicht feiner aufgelöst veröffentlicht wird. Die Antwort weist die Region deshalb offen aus.",
        },
        {
          q: "Sind die Jahre direkt vergleichbar?",
          a: "Mit Vorsicht. Erfassungsregeln und Straftatengruppen können sich ändern, deshalb trägt jede Antwort die Version der Statistik. Ein Vergleich sollte immer dieselbe Version und dieselbe Gruppe zugrunde legen.",
        },
        {
          q: "Gibt es Tatorte auf Straßenebene?",
          a: "Nein. Die PKS wird je Kreis veröffentlicht, feinere Geodaten gibt die Quelle nicht her. Alles, was danach aussähe, wäre eine Schätzung.",
        },
      ],
      datasetName: "Polizeiliche Kriminalstatistik je deutscher Stadt",
      datasetDesc: "Fallzahlen, Häufigkeitszahlen und Aufklärungsquoten je Hauptstraftatengruppe und Stadt aus der PKS des Bundeskriminalamts.",
    },
    en: {
      slug: "crime-statistics-api",
      metaTitle: "Crime statistics API Germany (PKS)",
      h1: "Crime statistics API for German cities (PKS)",
      lead: "A bare case count says little as long as the population next to it is missing. This API therefore returns three figures per main offence group: cases, frequency per 100,000 inhabitants and clearance rate, straight from the police crime statistics of the German Federal Criminal Police Office. Key-free, with reference year and version in every response.",
      dataDesc:
        "Per city the endpoint returns the reference year, the version of the statistic and, per main offence group, the number of cases, the frequency per 100,000 inhabitants and the clearance rate in percent. The group for all offences is included, so the total and its parts come in the same response.",
      sourceName: "Police crime statistics (PKS) - Bundeskriminalamt",
      sourceUrl: "https://www.bka.de/DE/AktuelleInformationen/StatistikenLagebilder/PolizeilicheKriminalstatistik/pks_node.html",
      license: "DL-DE/BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Reference year", "Version of the statistic", "Main offence group with label", "Number of cases", "Frequency per 100,000 inhabitants", "Clearance rate in percent"],
      keywords: ["crime statistics API", "PKS API", "German crime data API", "crime rate per district", "clearance rate open data"],
      coverageNote: "All cities in the register. The PKS is published per district and district-free city: if a city is not a district of its own, the value applies to the surrounding district, not to the city boundary. Reference year and version are part of every response because the Federal Criminal Police Office requires both in the attribution.",
      faq: [
        {
          q: "What is the frequency figure?",
          a: "The number of cases per 100,000 inhabitants. It makes regions of different size comparable, whereas the raw case count mostly mirrors population size.",
        },
        {
          q: "Does the value apply to the city or to the district?",
          a: "For a district-free city it applies to the city itself. If the city sits inside a rural district, the reported value is the district value because the PKS is not published at a finer resolution. The response names the region openly.",
        },
        {
          q: "Are years directly comparable?",
          a: "Only with care. Recording rules and offence groups can change, which is why every response carries the version of the statistic. A comparison should use the same version and the same group.",
        },
        {
          q: "Are crime scenes available at street level?",
          a: "No. The PKS is published per district and the source provides no finer geodata. Anything that looked like it would be an estimate.",
        },
      ],
      datasetName: "Police crime statistics per German city",
      datasetDesc: "Cases, frequency figures and clearance rates per main offence group and city from the PKS of the German Federal Criminal Police Office.",
    },
  },
  {
    id: "accidents",
    endpointId: "getCityAccidents",
    examplePath: "/api/v1/cities/koeln/accidents",
    coverageKey: "all",
    de: {
      slug: "unfallatlas-api",
      metaTitle: "Unfallatlas-API Deutschland, keylos",
      h1: "Unfallatlas-API für deutsche Städte",
      lead: "Wie viele Verkehrsunfälle mit Personenschaden ein Jahr in einer Stadt gebracht hat und wie viele davon Radfahrer oder Fußgänger betrafen: der Unfallatlas der Statistischen Ämter beantwortet das, diese API macht es je Stadt in einem einzigen GET-Request abrufbar. Ohne Schlüssel, mit dem Berichtsjahr an jeder Zahl.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt das Berichtsjahr, die Gesamtzahl der Unfälle mit Personenschaden und die Aufteilung nach Unfallkategorie: Unfälle mit Getöteten, mit Schwerverletzten und mit Leichtverletzten. Dazu kommen die Unfälle mit Beteiligung von Fahrrad, Fußgänger, Pkw und Motorrad sowie der amtliche Kreisschlüssel. Gezählt werden Unfälle, nicht Personen: ein Unfall mit drei Verletzten ist ein Fall.",
      sourceName: "Statistische Ämter des Bundes und der Länder, Unfallatlas",
      sourceUrl: "https://unfallatlas.statistikportal.de/",
      license: "DL-DE/BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Berichtsjahr", "Unfälle mit Personenschaden insgesamt", "Unfälle mit Getöteten", "Unfälle mit Schwerverletzten", "Unfälle mit Leichtverletzten", "Unfälle mit Fahrradbeteiligung", "Unfälle mit Fußgängerbeteiligung", "Unfälle mit Pkw-Beteiligung", "Unfälle mit Motorradbeteiligung", "Amtlicher Kreisschlüssel"],
      keywords: ["Unfallatlas API", "Verkehrsunfaelle Daten", "Unfallstatistik API Deutschland", "Radunfaelle Kreis Daten", "Unfalldaten Open Data"],
      coverageNote: "Alle Städte im Register. Die Aggregation erfolgt je fünfstelligem Kreisschlüssel: bildet eine Stadt keinen eigenen Kreis, gilt der Wert für den umgebenden Kreis. Die drei Unfallkategorien summieren sich exakt auf die Gesamtzahl, weil jeder Unfall genau eine Kategorie hat.",
      faq: [
        {
          q: "Sind das Unfälle oder Verletzte?",
          a: "Unfälle. Die Kategorie richtet sich nach der schwersten Folge: ein Unfall mit einem Getöteten und zwei Leichtverletzten zählt als Unfall mit Getöteten. Personenzahlen liefert die Quelle in dieser Aufbereitung nicht.",
        },
        {
          q: "Warum gibt es keine Einzelunfälle mit Koordinaten?",
          a: "Der Unfallatlas führt je Unfall einen Punkt, InfraNode liefert daraus die Jahressumme je Kreis. Das hält die Antwort klein und verhindert, dass einzelne Unfälle über die API rückverfolgbar werden.",
        },
        {
          q: "Gilt der Wert für die Stadt oder für den Kreis?",
          a: "Für kreisfreie Städte stadtgenau. Sonst ist es der Wert des umgebenden Kreises, und der Kreisschlüssel in der Antwort macht das nachvollziehbar.",
        },
        {
          q: "Wie aktuell sind die Zahlen?",
          a: "Der Unfallatlas erscheint jährlich. Jede Antwort trägt das Berichtsjahr, sodass sichtbar ist, auf welchen Zeitraum sich die Zahlen beziehen.",
        },
      ],
      datasetName: "Verkehrsunfälle je deutscher Stadt",
      datasetDesc: "Unfälle mit Personenschaden je Stadt und Berichtsjahr nach Unfallkategorie und beteiligter Verkehrsart aus dem Unfallatlas.",
    },
    en: {
      slug: "road-accidents-api",
      metaTitle: "Road accident API Germany, key-free",
      h1: "Road accident API for German cities",
      lead: "How many injury accidents a year brought to a city, and how many of them involved cyclists or pedestrians: the accident atlas of the German statistical offices answers that, and this API makes it available per city in a single GET request. No key, with the reference year attached to every figure.",
      dataDesc:
        "Per city the endpoint returns the reference year, the total number of accidents involving personal injury and the split by accident category: accidents with fatalities, with serious injuries and with slight injuries. It also returns the accidents involving a bicycle, a pedestrian, a car or a motorcycle, plus the official district key. Accidents are counted, not people: one accident with three injured is one case.",
      sourceName: "German federal and state statistical offices, accident atlas",
      sourceUrl: "https://unfallatlas.statistikportal.de/",
      license: "DL-DE/BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Reference year", "Accidents with personal injury in total", "Accidents with fatalities", "Accidents with serious injuries", "Accidents with slight injuries", "Accidents involving a bicycle", "Accidents involving a pedestrian", "Accidents involving a car", "Accidents involving a motorcycle", "Official district key"],
      keywords: ["road accident API", "German accident data", "traffic accident statistics API", "cycling accidents district data", "accident open data"],
      coverageNote: "All cities in the register. The aggregation runs per five digit district key: if a city is not a district of its own, the value applies to the surrounding district. The three accident categories add up exactly to the total because every accident has exactly one category.",
      faq: [
        {
          q: "Are these accidents or casualties?",
          a: "Accidents. The category follows the most severe outcome: an accident with one fatality and two slight injuries counts as an accident with fatalities. Casualty counts are not part of this aggregation.",
        },
        {
          q: "Why are there no individual accidents with coordinates?",
          a: "The accident atlas carries one point per accident, and InfraNode aggregates that into the yearly total per district. This keeps responses small and prevents individual accidents from being traceable through the API.",
        },
        {
          q: "Does the value apply to the city or the district?",
          a: "For district-free cities it applies to the city. Otherwise it is the value of the surrounding district, and the district key in the response makes that explicit.",
        },
        {
          q: "How current are the numbers?",
          a: "The accident atlas is published annually. Every response carries the reference year, so the period the numbers cover is always visible.",
        },
      ],
      datasetName: "Road accidents per German city",
      datasetDesc: "Accidents involving personal injury per city and reference year by accident category and mode involved, from the German accident atlas.",
    },
  },
  {
    id: "unemployment",
    endpointId: "getCityUnemployment",
    examplePath: "/api/v1/cities/koeln/unemployment",
    coverageKey: "all",
    de: {
      slug: "arbeitsmarkt-api",
      metaTitle: "Arbeitsmarkt-API Deutschland, keylos",
      h1: "Arbeitsmarkt-API für deutsche Städte",
      lead: "Arbeitslosenzahl und Quote sind meist nur der Einstieg, danach kommt die Frage, wie die Stadt bei Einkommen, Wohnen oder Erreichbarkeit dasteht. Diese API liefert beides: die amtlichen Arbeitsmarktzahlen und mehr als 60 INKAR-Indikatoren des BBSR, je Stadt und ohne Schlüssel.",
      dataDesc:
        "Ein Endpunkt liefert die Zahl der Arbeitslosen, die Arbeitslosenquote in Prozent, das Berichtsjahr und den amtlichen Namen der Region. Ein zweiter Endpunkt liefert die INKAR-Indikatoren des BBSR: je Indikator die Bezeichnung samt Einheit, den Wert, das Jahr und die Themenkategorie, darunter Arbeitsmarkt, Wirtschaft, Einkommen, Demografie, Wohnen, Erreichbarkeit, Bildung und Gesundheit. Es sind mehr als 60 Indikatoren je Stadt.",
      sourceName: "Statistische Ämter des Bundes und der Länder (Arbeitsmarkt) und Bundesinstitut für Bau-, Stadt- und Raumforschung (BBSR), INKAR",
      sourceUrl: "https://www.inkar.de/",
      license: "DL-DE/BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Arbeitslose", "Arbeitslosenquote in Prozent", "Berichtsjahr", "Amtlicher Name der Region", "Indikator-Bezeichnung mit Einheit", "Indikator-Wert", "Jahr des Indikators", "Themenkategorie des Indikators"],
      keywords: ["Arbeitslosenquote API", "Arbeitsmarkt Daten API", "INKAR API", "BBSR Indikatoren Daten", "Arbeitslose Kreis Open Data"],
      coverageNote: "Alle Städte im Register. Beide Quellen liegen je Kreis und kreisfreier Stadt vor: bildet eine Stadt keinen eigenen Kreis, gilt der Wert für den umgebenden Kreis. Je INKAR-Indikator wird der jüngste verfügbare Jahreswert geführt, unverändert aus der Quelle.",
      faq: [
        {
          q: "Nach welcher Definition ist die Quote berechnet?",
          a: "Es ist der von der amtlichen Statistik für die Region gemeldete Wert. InfraNode rechnet nichts um und bildet keine eigene Quote, deshalb steht das Berichtsjahr immer dabei.",
        },
        {
          q: "Warum weicht der INKAR-Arbeitslosen-Indikator von der Quote ab?",
          a: "Weil es zwei Kennzahlen mit unterschiedlicher Bezugsgröße und unterschiedlichem Jahr sind: INKAR führt den Anteil der Arbeitslosen an den zivilen Erwerbspersonen für das jüngste dort verfügbare Jahr, der Arbeitsmarkt-Endpunkt die amtlich gemeldete Quote des Berichtsjahres. Beide Werte tragen ihr Jahr, damit die Differenz erklärbar bleibt.",
        },
        {
          q: "Welche Themen deckt das Indikator-Set ab?",
          a: "Arbeitsmarkt, Wirtschaft, Einkommen, Demografie, Wohnen, Erreichbarkeit, Verkehr, Bildung, Gesundheit und Fläche. Jeder Indikator trägt seine Kategorie, sodass sich ein Thema gezielt herausfiltern lässt.",
        },
        {
          q: "Sind die Werte tagesaktuell?",
          a: "Nein, beide Quellen veröffentlichen jährlich. Der Endpunkt liest aus einem vorgehaltenen Datensatz, es gibt keinen Upstream-Abruf im Request-Pfad, und das Jahr steht in jeder Antwort.",
        },
      ],
      datasetName: "Arbeitsmarkt und sozioökonomische Indikatoren je deutscher Stadt",
      datasetDesc: "Arbeitslose und Arbeitslosenquote je Stadt sowie mehr als 60 INKAR-Indikatoren des BBSR mit Wert, Jahr und Themenkategorie.",
    },
    en: {
      slug: "labour-market-api",
      metaTitle: "Labour market API Germany, key-free",
      h1: "Labour market API for German cities",
      lead: "Unemployment figures and the rate are usually just the entry point, followed by the question of how the city stands on income, housing or accessibility. This API returns both: the official labour market figures and more than 60 INKAR indicators of the BBSR, per city and without a key.",
      dataDesc:
        "One endpoint returns the number of unemployed, the unemployment rate in percent, the reference year and the official name of the region. A second endpoint returns the INKAR indicators of the BBSR: per indicator the label including its unit, the value, the year and the topic category, covering labour market, economy, income, demography, housing, accessibility, education and health. There are more than 60 indicators per city.",
      sourceName: "German federal and state statistical offices (labour market) and Federal Institute for Research on Building, Urban Affairs and Spatial Development (BBSR), INKAR",
      sourceUrl: "https://www.inkar.de/",
      license: "DL-DE/BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Unemployed persons", "Unemployment rate in percent", "Reference year", "Official name of the region", "Indicator label including unit", "Indicator value", "Year of the indicator", "Topic category of the indicator"],
      keywords: ["unemployment rate API", "labour market data API", "INKAR API", "BBSR indicators data", "unemployment district open data"],
      coverageNote: "All cities in the register. Both sources are published per district and district-free city: if a city is not a district of its own, the value applies to the surrounding district. Per INKAR indicator the most recent available yearly value is carried, unchanged from the source.",
      faq: [
        {
          q: "Which definition is the rate based on?",
          a: "It is the value reported by the official statistics for that region. InfraNode does not recalculate anything and does not derive its own rate, which is why the reference year is always included.",
        },
        {
          q: "Why does the INKAR unemployment indicator differ from the rate?",
          a: "Because they are two figures with a different base and a different year: INKAR carries the share of unemployed among the civilian labour force for the most recent year available there, while the labour market endpoint carries the officially reported rate of its reference year. Both values carry their year so the difference stays explainable.",
        },
        {
          q: "Which topics does the indicator set cover?",
          a: "Labour market, economy, income, demography, housing, accessibility, transport, education, health and land use. Every indicator carries its category so a single topic can be filtered out.",
        },
        {
          q: "Are the values updated daily?",
          a: "No, both sources publish annually. The endpoint reads from a stored dataset, there is no upstream call in the request path, and the year is part of every response.",
        },
      ],
      datasetName: "Labour market and socioeconomic indicators per German city",
      datasetDesc: "Unemployed persons and unemployment rate per city plus more than 60 INKAR indicators of the BBSR with value, year and topic category.",
    },
  },
  {
    id: "business-registrations",
    endpointId: "getCityBusinessRegistrations",
    examplePath: "/api/v1/cities/koeln/business-registrations",
    coverageKey: "all",
    de: {
      slug: "gewerbedaten-api",
      metaTitle: "Gewerbedaten-API Deutschland, keylos",
      h1: "Gewerbe- und Insolvenzdaten-API für deutsche Städte",
      lead: "An Gewerbeanmeldungen, Abmeldungen und beantragten Insolvenzen lässt sich ablesen, wie es der Wirtschaft einer Stadt geht. Diese API gibt diese Zahlen je Stadt heraus, aus der Regionaldatenbank Deutschland, keylos und jeweils mit dem Berichtsjahr, das dahintersteht.",
      dataDesc:
        "Ein Endpunkt liefert die Zahl der Gewerbeanmeldungen, die Zahl der Gewerbeabmeldungen, den Saldo aus beiden und das Berichtsjahr. Ein zweiter Endpunkt liefert die beantragten Insolvenzen, getrennt nach Unternehmen und übrigen Schuldnern, ebenfalls mit Berichtsjahr. Die Berichtsjahre der beiden Endpunkte können auseinanderliegen, weil die Statistiken unterschiedlich schnell veröffentlicht werden.",
      sourceName: "Statistische Ämter des Bundes und der Länder, Regionaldatenbank Deutschland",
      sourceUrl: "https://www.regionalstatistik.de/",
      license: "DL-DE/BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Gewerbeanmeldungen", "Gewerbeabmeldungen", "Saldo aus An- und Abmeldungen", "Berichtsjahr der Gewerbeanzeigen", "Beantragte Unternehmensinsolvenzen", "Beantragte Insolvenzen übriger Schuldner", "Berichtsjahr der Insolvenzen"],
      keywords: ["Gewerbeanmeldungen API", "Insolvenzen Daten API", "Gewerbeabmeldungen Kreis", "Unternehmensinsolvenzen Open Data", "Gewerbedaten Deutschland API"],
      coverageNote: "Alle Städte im Register. Beide Statistiken liegen je Kreis und kreisfreier Stadt vor: bildet eine Stadt keinen eigenen Kreis, gilt der Wert für den umgebenden Kreis. Der Saldo ist die Differenz aus An- und Abmeldungen des jeweiligen Berichtsjahres, keine Bestandsgröße.",
      faq: [
        {
          q: "Ist eine Gewerbeanmeldung dasselbe wie eine Firmengründung?",
          a: "Nein. Angemeldet wird jedes Gewerbe, auch Nebentätigkeiten, Umzüge in die Stadt und Übernahmen. Die Zahl beschreibt die Bewegung am Gewerberegister, nicht die Zahl neuer Unternehmen.",
        },
        {
          q: "Was bedeutet beantragte Insolvenz?",
          a: "Gezählt werden gestellte Insolvenzanträge, nicht eröffnete oder abgeschlossene Verfahren. Deshalb ist die Zahl ein Frühindikator und nicht mit einer Statistik über Verfahrensausgänge zu verwechseln.",
        },
        {
          q: "Warum tragen die zwei Endpunkte unterschiedliche Jahre?",
          a: "Weil die Gewerbeanzeigen früher veröffentlicht werden als die Insolvenzstatistik. Jede Antwort trägt ihr eigenes Berichtsjahr, damit nicht versehentlich über verschiedene Zeiträume hinweg verglichen wird.",
        },
        {
          q: "Gibt es die Zahlen je Branche?",
          a: "Nein, dieser Endpunkt liefert die Summen je Kreis und Jahr. Eine Aufschlüsselung nach Wirtschaftszweig gibt die genutzte Tabelle in dieser Auflösung nicht her.",
        },
      ],
      datasetName: "Gewerbeanzeigen und Insolvenzen je deutscher Stadt",
      datasetDesc: "Gewerbeanmeldungen, Gewerbeabmeldungen und Saldo je Stadt sowie beantragte Insolvenzen von Unternehmen und übrigen Schuldnern aus der Regionaldatenbank Deutschland.",
    },
    en: {
      slug: "business-data-api",
      metaTitle: "Business data API Germany, key-free",
      h1: "Business and insolvency API for German cities",
      lead: "Business registrations, deregistrations and filed insolvencies show how the economy of a city is doing. This API returns those figures per city from the regional database Germany, key-free and each with the reference year behind it.",
      dataDesc:
        "One endpoint returns the number of business registrations, the number of deregistrations, the balance of both and the reference year. A second endpoint returns filed insolvencies, split into companies and other debtors, also with a reference year. The reference years of the two endpoints can differ because the statistics are published at a different pace.",
      sourceName: "German federal and state statistical offices, regional database Germany",
      sourceUrl: "https://www.regionalstatistik.de/",
      license: "DL-DE/BY 2.0",
      licenseUrl: "https://www.govdata.de/dl-de/by-2-0",
      vars: ["Business registrations", "Business deregistrations", "Balance of registrations and deregistrations", "Reference year of the business notifications", "Filed corporate insolvencies", "Filed insolvencies of other debtors", "Reference year of the insolvencies"],
      keywords: ["business registrations API", "insolvency data API", "German business data API", "corporate insolvencies open data", "business deregistrations district"],
      coverageNote: "All cities in the register. Both statistics are published per district and district-free city: if a city is not a district of its own, the value applies to the surrounding district. The balance is the difference between registrations and deregistrations in that reference year, not a stock figure.",
      faq: [
        {
          q: "Is a business registration the same as a company founding?",
          a: "No. Every trade is registered, including secondary activities, relocations into the city and takeovers. The figure describes movement in the trade register, not the number of new companies.",
        },
        {
          q: "What does a filed insolvency mean?",
          a: "Filed insolvency petitions are counted, not opened or completed proceedings. That makes the figure an early indicator and not a statistic about outcomes of proceedings.",
        },
        {
          q: "Why do the two endpoints carry different years?",
          a: "Because business notifications are published earlier than the insolvency statistic. Every response carries its own reference year so that different periods are not compared by accident.",
        },
        {
          q: "Are the figures available per industry?",
          a: "No, this endpoint returns the totals per district and year. The underlying table does not provide a breakdown by economic sector at this resolution.",
        },
      ],
      datasetName: "Business notifications and insolvencies per German city",
      datasetDesc: "Business registrations, deregistrations and balance per city plus filed insolvencies of companies and other debtors from the regional database Germany.",
    },
  },
  {
    id: "sustainability",
    endpointId: "getCitySustainability",
    examplePath: "/api/v1/cities/koeln/sustainability",
    coverageKey: "all",
    de: {
      slug: "nachhaltigkeit-api",
      metaTitle: "Nachhaltigkeits-API Deutschland (SDG), keylos",
      h1: "Nachhaltigkeits-API für deutsche Städte (SDG-Indikatoren)",
      lead: "Wie nachhaltig eine Stadt dasteht, hängt nicht an einer Zahl, sondern an einem ganzen Satz von Kennzahlen: Flächenverbrauch, Kinderarmut, Ladepunkte, Naturschutzflächen, Trinkwasserverbrauch. Diese API liefert bis zu 53 kommunale Nachhaltigkeitsindikatoren je Stadt als Zeitreihe von 2006 bis 2023, keylos und mit Jahr an jedem Wert.",
      dataDesc:
        "Pro Stadt liefert der Endpunkt einen Satz Indikatoren, jeder mit stabilem Schlüssel, Bezeichnung, Einheit, der Quellenangabe des Statistikamtes und einer Erläuterung, wie der Wert zu lesen ist. Dazu kommt je Indikator die vollständige Jahresreihe aus Jahr und Wert sowie das jüngste Jahr mit seinem Wert. Auf der Ebene der Antwort stehen die Zahl der Indikatoren, die abgedeckte Jahresspanne, der amtliche Gemeindeschlüssel und die Wikidata-ID. Mit den Parametern from und to lässt sich die Reihe auf ein Jahresfenster einschränken.",
      sourceName: "Wegweiser Kommune, Bertelsmann Stiftung",
      sourceUrl: "https://www.wegweiser-kommune.de/",
      license: "CC0 1.0",
      licenseUrl: "https://creativecommons.org/publicdomain/zero/1.0/",
      vars: ["Indikator-Schlüssel und Bezeichnung", "Einheit des Indikators", "Quellenangabe je Indikator", "Erläuterung zur Lesart", "Jüngstes Jahr und jüngster Wert", "Jahresreihe aus Jahr und Wert", "Zahl der Indikatoren", "Abgedeckte Jahresspanne", "Amtlicher Gemeindeschlüssel (AGS)", "Wikidata-ID der Stadt"],
      keywords: ["Nachhaltigkeit API", "SDG Indikatoren API", "Wegweiser Kommune API", "kommunale Nachhaltigkeitsindikatoren", "SDG Kommunen Open Data"],
      coverageNote: "Alle Städte im Register liefern Daten. Der Umfang unterscheidet sich: kreisfreie Städte kommen auf bis zu 53 Indikatoren, kreisangehörige Städte auf weniger, weil ein Teil der Kennzahlen nur ab Kreisebene erhoben wird. Live gemessen: Köln und München 53, Berlin 52, Hamburg 51, Hannover 44, Aachen 43.",
      faq: [
        {
          q: "Welche Themen deckt das Indikatorenset ab?",
          a: "Es folgt den Nachhaltigkeitszielen der Vereinten Nationen auf kommunaler Ebene und reicht deshalb weit über Umweltthemen hinaus: Flächen- und Naturschutz, Luft und Wasser, Energie und Elektromobilität, Armut und soziale Lage, Bildung, Gesundheit, Wohnen und Mieten, Beschäftigung und Teilhabe sowie kommunale Finanzen.",
        },
        {
          q: "Wie schränke ich die Zeitreihe auf einzelne Jahre ein?",
          a: "Über die Parameter from und to, beide als Jahreszahl. Das verkleinert die Antwort deutlich: Köln ungefiltert rund 82 Kilobyte, mit from=2023 und to=2023 rund 24 Kilobyte. Ungültige Jahre führen zu 400, und die Angaben zum jüngsten Jahr beziehen sich immer auf den jüngsten Punkt im gewählten Fenster.",
        },
        {
          q: "Sind das amtliche SDG-Zahlen der Stadt selbst?",
          a: "Nein. Die Indikatoren stammen aus dem Wegweiser Kommune der Bertelsmann Stiftung, der sie aus amtlichen Statistiken einheitlich für alle Gemeinden berechnet. Genau deshalb sind Städte untereinander vergleichbar. Jeder Indikator trägt seine Quellenangabe und seine Erläuterung mit, sodass die Herkunft jedes Wertes nachvollziehbar bleibt.",
        },
        {
          q: "Warum liefert meine Stadt weniger Indikatoren als eine andere?",
          a: "Weil ein Teil der Kennzahlen erst ab Kreisebene erhoben wird. Für kreisangehörige Städte fehlen diese Indikatoren, statt sie mit dem Kreiswert aufzufüllen. Die Antwort führt die Zahl der tatsächlich vorhandenen Indikatoren mit, und Städte ohne eingelesenen Bestand melden das offen als Status, statt einen Wert zu erfinden.",
        },
      ],
      datasetName: "Kommunale Nachhaltigkeits- und SDG-Indikatoren je deutscher Stadt",
      datasetDesc: "Bis zu 53 Nachhaltigkeitsindikatoren je Stadt als Jahresreihe von 2006 bis 2023 aus dem Wegweiser Kommune, je Indikator mit Einheit, Quelle und Erläuterung.",
    },
    en: {
      slug: "sustainability-api",
      metaTitle: "Sustainability API Germany (SDG), key-free",
      h1: "Sustainability API for German cities (SDG indicators)",
      lead: "How sustainable a city is does not come down to a single number but to a whole set of measures: land consumption, child poverty, charging points, protected areas, drinking water use. This API returns up to 53 municipal sustainability indicators per city as a time series from 2006 to 2023, key-free and with the year attached to every value.",
      dataDesc:
        "Per city the endpoint returns a set of indicators, each with a stable key, a label, a unit, the attribution of the statistical office and an explanation of how to read the value. Each indicator also carries its full yearly series of year and value plus the most recent year with its value. At response level you get the number of indicators, the covered year range, the official municipality key and the Wikidata ID. The parameters from and to narrow the series down to a year window.",
      sourceName: "Wegweiser Kommune, Bertelsmann Stiftung",
      sourceUrl: "https://www.wegweiser-kommune.de/",
      license: "CC0 1.0",
      licenseUrl: "https://creativecommons.org/publicdomain/zero/1.0/",
      vars: ["Indicator key and label", "Unit of the indicator", "Attribution per indicator", "Explanation of how to read it", "Most recent year and value", "Yearly series of year and value", "Number of indicators", "Covered year range", "Official municipality key (AGS)", "Wikidata ID of the city"],
      keywords: ["sustainability API", "SDG indicators API", "Wegweiser Kommune API", "municipal sustainability indicators", "SDG cities open data"],
      coverageNote: "All cities in the register return data. The scope differs: district-free cities reach up to 53 indicators, cities inside a district fewer, because part of the measures is only collected at district level. Measured live: Cologne and Munich 53, Berlin 52, Hamburg 51, Hanover 44, Aachen 43.",
      faq: [
        {
          q: "Which topics does the indicator set cover?",
          a: "It follows the Sustainable Development Goals of the United Nations at municipal level and therefore reaches well beyond environmental topics: land use and nature protection, air and water, energy and electric mobility, poverty and social situation, education, health, housing and rents, employment and participation as well as municipal finances.",
        },
        {
          q: "How do I narrow the time series to specific years?",
          a: "Through the parameters from and to, both as a year. This shrinks the response considerably: Cologne unfiltered is around 82 kilobytes, with from=2023 and to=2023 around 24 kilobytes. Invalid years return 400, and the most recent year and value always refer to the most recent point inside the selected window.",
        },
        {
          q: "Are these the official SDG figures of the city itself?",
          a: "No. The indicators come from Wegweiser Kommune of the Bertelsmann Stiftung, which derives them from official statistics uniformly for all municipalities. That is exactly why cities are comparable with each other. Every indicator carries its attribution and its explanation, so the origin of each value stays traceable.",
        },
        {
          q: "Why does my city return fewer indicators than another one?",
          a: "Because part of the measures is only collected at district level. For cities inside a district those indicators are missing rather than filled in with the district value. The response carries the number of indicators actually present, and cities without an ingested set report that openly as a status instead of inventing a value.",
        },
      ],
      datasetName: "Municipal sustainability and SDG indicators per German city",
      datasetDesc: "Up to 53 sustainability indicators per city as a yearly series from 2006 to 2023 from Wegweiser Kommune, each with unit, attribution and explanation.",
    },
  },
];

export function topicCityCount(
  topic: Topic,
  coverage: { total_cities: number; partial: Record<string, string[]> },
): number {
  if (topic.coverageKey === "all") return coverage.total_cities;
  return coverage.partial[topic.coverageKey]?.length ?? 0;
}
