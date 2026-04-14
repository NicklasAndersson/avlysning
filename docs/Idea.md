Systemarkitektur: Karta över Försvarsmaktens Övningsfält

Detta dokument beskriver arkitekturen för en tjänst som visar aktiva avlysningar för Försvarsmaktens (FM) övnings- och skjutfält. Tjänsten är byggd med fokus på låga driftkostnader, oberoende av externa API:er, och en "Offline-First"-upplevelse för användare i fält.

1. Systemets Komponenter

Systemet är uppdelat i fyra frikopplade huvuddelar:

1.1 Frontend (PWA)

Plattform: Cloudflare Pages

Teknik: Statisk HTML/CSS/JS (React, Vue eller Vanilla JS) som en Progressive Web App (PWA).

Funktion: Visar kartan, användarens GPS-position och avlysta områden. Cachar allt för offline-bruk med hjälp av Service Workers.

1.2 Datalager & Kartserver (Cloudflare R2)

Funktion: Agerar både filserver för appens JSON-data och "kartserver".

Filer:

skjutfalt_status.json (Innehåller extraherad data från PDF:er: fält, datum, tider).

sync_status.json (Flagga som visar om en ny PDF har upptäckts men ännu inte bearbetats).

Kartdata: Statiska kartfiler (se avsnitt 4).

1.3 Backend / Skrapa (Lokal Hemmaserver)

Plattform: Egen hårdvara (Raspberry Pi/Hemmaserver).

Teknik: Docker, Python (t.ex. pdfplumber, requests), Cron.

Funktion: Körs på schema (t.ex. via lokalt Cron-jobb). Laddar ner PDF:er från FM, extraherar texten, mappar tider/datum till specifika fält (polygoner) och genererar en uppdaterad skjutfalt_status.json som laddas upp till Cloudflare R2.

1.4 Watchdog (Cloudflare Worker)

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

3.1 PMTiles & MapLibre GL JS

Lösningen bygger på PMTiles, vilket är ett format som lagrar en hel planet (eller ett land) av kartplattor i en enda fil.

Kartklient i Frontend: MapLibre GL JS. Ett open-source bibliotek för att rendera interaktiva kartor.

Hosting av Kartan: En fil, t.ex. sweden.pmtiles (skapad från OpenStreetMap-data), laddas upp till er Cloudflare R2-bucket.

Hur det fungerar: MapLibre med PMTiles-tillägget använder HTTP Range Requests för att hämta exakt de kartplattor användaren tittar på direkt från S3/R2-bucketen, helt utan behov av en traditionell kartserver (som GeoServer eller liknande).

3.2 Geodata för Övningsfälten (Polygoner)

Gränserna för Försvarsmaktens skjutfält laddas ner som öppna geodata (från Lantmäteriet eller FM) och konverteras till GeoJSON. Dessa GeoJSON-filer ritas ut som ett lager (Layer) ovanpå baskartan i MapLibre.

4. UX och Juridisk Ansvarsfriskrivning

Eftersom tjänsten hanterar säkerhetskritisk information måste designen vara transparent med systemets status.

Tydlig Tidsstämpel: Appen måste alltid visa datum och tid för när datan (PDF:en) senast skrapades framgångsrikt.

Offline-indikator: Om PWA:n upptäcker att internetuppkoppling saknas, ska UI:t övergå till ett "Offline Mode" (t.ex. gul temafärg) som tydligt informerar användaren om att datan kan vara inaktuell.

Ansvarsfriskrivning (Disclaimer): Appen får ej utge sig för att vara en officiell Försvarsmakts-kanal. Det måste framgå tydligt i appen att det alltid är den fysiska skyltningen (bommar, röda lampor, varningsskyltar) på plats vid fältet som gäller rent juridiskt, oavsett vad appen säger.