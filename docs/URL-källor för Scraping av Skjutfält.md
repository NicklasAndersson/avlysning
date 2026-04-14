URL-källor för Scraping av Skjutfält

Denna tabell innehåller de exakta webbadresserna (URL) som behövs för att automatisera nedladdning av skjutvarningar och tillträdesförbud för svenska skjutfält.

1. Försvarsmakten (Huvudkällor)

Försvarsmakten samlar den absoluta merparten av alla skjutvarningar (i PDF-format) på sin centrala sida. Länken nedan är den absolut viktigaste att skrapa. Vissa stora fält (som Älvdalen och Tåme) har dock brutits ut till egna undersidor.

Skjutfält / Resurs

Innehåll för scraping

Exakt Webbadress (URL)

Samlingssidan (Alla Regementen)

Här finns PDF-länkar i dragspelsmenyer för t.ex. Arvidsjaur, Berga, Björka, Revingehed, Utö m.fl.

https://www.forsvarsmakten.se/regler-och-tillstand/skjutfalt-och-forbud/

Älvdalens skjutfält

Skjutvarningar specifikt för Älvdalen.

https://www.forsvarsmakten.se/regler-och-tillstand/skjutfalt-och-forbud/alvdalens-skjutfalt/

Tåme skjutfält

Skjutvarningar specifikt för Tåme.

https://www.forsvarsmakten.se/regler-och-tillstand/skjutfalt-och-forbud/tame-skjutfalt/

Stockholms Amfibieregemente

Specifik sida för skärgården (Korsö, Mellsten, Utö etc). Finns ibland även på samlingssidan ovan.

https://www.forsvarsmakten.se/sv/organisation/stockholms-amfibieregemente-amf-1/stockholms-amfibieregementes-skjutfalt-och-tilltradesforbud/

2. Försvarsindustrin (Testcenter)

Dessa fält ägs ofta helt eller delvis av industrin (t.ex. Saab Bofors) och hanteras via egna fristående webbplatser, ofta med data direkt i HTML istället för PDF.

Skjutfält / Resurs

Innehåll för scraping

Exakt Webbadress (URL)

Bofors / Villingsbergs skjutfält

Sektorbaserad data (Sektor 1-10, A-E) i tabellformat/HTML. Extremt strukturerad.

https://skjutfalten.se/

Bofors - Direktsida för avlysningar

Listar dagens och kommande avlysningar.

https://skjutfalten.se/om-skjutfalten/

3. Kommunala Informationssidor

I många fall hjälper kommunerna till att sprida Försvarsmaktens tillträdesförbud via sina egna hemsidor. Detta kan ibland vara lättare att skrapa än FM:s PDF:er då kommuner ofta lägger ut informationen som vanlig text (HTML) i tabeller.

Skjutfält / Resurs

Kommun

Exakt Webbadress (URL)

Falun Skjutfält

Falu Kommun

https://www.falun.se/stod--omsorg/trygg-och-saker/skjutvarningar-pa-militaromradet.html

Härads skjutfält

Strängnäs Kommun

https://www.strangnas.se/bygga-bo-och-miljo/naturomraden-och-parker/harads-skjutfalt

Remmene skjutfält

Vårgårda Kommun

https://www.vargarda.se/bo-bygga-och-miljo/remmene-skjutfalt.html

Strategi för Skrapan (Python)

Ett bra första steg är att fokusera enbart på https://www.forsvarsmakten.se/regler-och-tillstand/skjutfalt-och-forbud/.

Använd biblioteket requests för att hämta HTML-koden från URL:en.

Leta efter alla <a>-taggar där href slutar på .pdf.

Filtrera länkarna så att du bara behåller de som innehåller orden skjutvarning eller tilltradesforbud.

Ladda ner dessa PDF:er till din Docker-container för vidare analys med t.ex. pdfplumber.