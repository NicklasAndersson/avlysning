# Systemarkitektur: Karta över Försvarsmaktens Övningsfält

> **Visionsdokument.** Beskriver den tänkta målarkitekturen. Se `docs/STATUS.md` för aktuellt implementationsläge.

Detta dokument beskriver arkitekturen för en tjänst som visar aktiva avlysningar för Försvarsmaktens (FM) övnings- och skjutfält. Tjänsten är byggd med fokus på låga driftkostnader, oberoende av externa API:er, och en "Offline-First"-upplevelse för användare i fält.

1. Systemets Komponenter

Systemet är uppdelat i fyra frikopplade huvuddelar:

1.1 Frontend (PWA) — ✅ Delvis implementerad

Plattform: Cloudflare Pages — ⏳ Ej deployad än

Teknik: React 19 + TypeScript + Vite 6 + MapLibre GL JS. ✅

Funktion: Visar kartan, användarens GPS-position och avlysta områden. ✅ Cachar allt för offline-bruk med hjälp av Service Workers. ⏳ PWA/Service Worker ej implementerad.

1.2 Datalager & Kartserver (Cloudflare R2) — ⏳ Ej implementerad

Funktion: Agerar både filserver för appens JSON-data och "kartserver".

> Lokalt: Data servas från `data/` via symlink i `frontend/public/data/`. ✅

Filer:

skjutfalt_status.json (Innehåller extraherad data från PDF:er: fält, datum, tider). ✅

field_config.json (Mappning FM-fältnamn → OSM polygon-ID:n). ✅

skjutfalt.geojson (313 militära polygoner från OSM/Geofabrik). ✅

sync_status.json (Flagga som visar om en ny PDF har upptäckts men ännu inte bearbetats). ⏳

Kartdata: PMTiles på R2. ⏳ Lokalt används OSM raster-tiles.

1.3 Backend / Skrapa (Lokal Hemmaserver) — ✅ Implementerad (lokalt)

Plattform: Lokal utvecklingsmaskin. Produktionsmål: Raspberry Pi / hemmaserver. ⏳

Teknik: Python 3.11+, pdfplumber, requests, beautifulsoup4. Docker-stöd finns. ✅

Funktion: Körs manuellt (CLI). Hämtar 75 fält via FM JSON API + 1 Bofors + 3 kommun. 19 PDF-parsers med formatdetektering. Genererar `skjutfalt_status.json`. ✅ Schemalagd körning (cron) är ej implementerad. ⏳

1.4 Watchdog (Cloudflare Worker) — ⏳ Ej implementerad

Funktion: En lättviktig process som körs via Cloudflare Cron (t.ex. var 5:e minut).

Flöde:

Kontrollerar ETags eller Last-Modified på FM:s informationssidor.

Om förändring upptäcks: Ändrar sync_status.json i R2 till {"update_pending": true}.

Skickar ett larm (Webhook till Discord/Telegram) till systemadministratören.

2. Dataflöde (Steg-för-steg)

Försvarsmakten publicerar en ny PDF.

Worker (Watchdog) upptäcker förändringen nästan omedelbart. Uppdaterar sync_status.json på R2.

Användare i fält som öppnar appen får direkt ett varningsmeddelande (via sync_status.json): "Observera: Ny data har publicerats av FM och bearbetas just nu."

Backend (Hemmaserver) kör sitt schemalagda jobb, parsar PDF:en och laddar upp en ny skjutfalt_status.json. Den återställer även sync_status.json till false.

Användare i fält får den nya datan indragen, varningen försvinner och kartan visar korrekt aktuell status.

3. Självhostad Kartmotor (Utan externa beroenden)

För att undvika externa beroenden som Google Maps eller Mapbox API, och för att garantera att tjänsten överlever utan tredjepartskostnader, används ett filbaserat kartformat lagrat direkt i Cloudflare R2.

3.1 PMTiles & MapLibre GL JS — ✅ MapLibre implementerad, ⏳ PMTiles ej

Lösningen bygger på PMTiles, vilket är ett format som lagrar en hel planet (eller ett land) av kartplattor i en enda fil.

Kartklient i Frontend: MapLibre GL JS. ✅ Implementerad med OSM raster-tiles för lokal utveckling.

Hosting av Kartan: En fil, t.ex. sweden.pmtiles (skapad från OpenStreetMap-data), laddas upp till er Cloudflare R2-bucket.

Hur det fungerar: MapLibre med PMTiles-tillägget använder HTTP Range Requests för att hämta exakt de kartplattor användaren tittar på direkt från S3/R2-bucketen, helt utan behov av en traditionell kartserver (som GeoServer eller liknande).

3.2 Geodata för Övningsfälten (Polygoner) — ✅ Implementerad

Gränserna för Försvarsmaktens skjutfält laddas ner som öppna geodata från OpenStreetMap (via Geofabrik + ogr2ogr) och sparas som GeoJSON. 313 polygoner (161 namngivna). Dessa GeoJSON-filer ritas ut som ett lager (Layer) ovanpå baskartan i MapLibre.

4. UX och Juridisk Ansvarsfriskrivning

Eftersom tjänsten hanterar säkerhetskritisk information måste designen vara transparent med systemets status.

Tydlig Tidsstämpel: Appen måste alltid visa datum och tid för när datan (PDF:en) senast skrapades framgångsrikt. ✅

Offline-indikator: Om PWA:n upptäcker att internetuppkoppling saknas, ska UI:t övergå till ett "Offline Mode" (t.ex. gul temafärg) som tydligt informerar användaren om att datan kan vara inaktuell. ⏳

Ansvarsfriskrivning (Disclaimer): Appen får ej utge sig för att vara en officiell Försvarsmakts-kanal. Det måste framgå tydligt i appen att det alltid är den fysiska skyltningen (bommar, röda lampor, varningsskyltar) på plats vid fältet som gäller rent juridiskt, oavsett vad appen säger. ✅