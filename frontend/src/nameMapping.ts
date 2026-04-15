/**
 * Mappning mellan FM:s officiella namn och GeoJSON (OSM) namn.
 * FM-namn → GeoJSON-namn (nyckel = FM-namn i lowercase).
 */

const FM_TO_GEO: Record<string, string> = {
  // Case-skillnader
  'tåme skjutfält': 'Tåme Skjutfält',
  'villingsbergs skjutfält': 'Villingsbergs Skjutfält',

  // Suffix-skillnader (FM lägger till ort)
  'dagsådalens skjutfält - östersund': 'Dagsådalens skjutfält',
  'kalixfors skjutfält – kiruna': 'Kalixfors skjutfält',

  // Namnvarianter
  'karlskrona inre öars övningsfält': 'Karlskrona inre öar övningsfält',
  'grebbegården övningsfält': 'Gräbbegården övningsfält',
  'skillingaryds skjutfält': 'Skillingaryds övnings- och skjutfält',
  'skogstibble skjutfält': 'Skogstibblefältet',
  'sågebackens skjutfält': 'Sågebackens skjutområde',
  'bråt skjutbanor – borås': 'Bråts skjutfällt',
  'vällinge övningsområde': 'Vällinge övnings- och skjutfält',

  // Sammansatta fält → en polygon
  'bodens södra och kusträsks övnings- och skjutfält': 'Bodens södra skjutfält',
  'härnösands, härnöns och skärsvikens skjutfält': 'Skärsvikens skjutfält',
  'lombens och orrträsks skjutfält': 'Lombens skjutfält',

  // Bofors / kommun-namn → OSM-namn
  'bofors skjutfält': 'SAAB Bofors Test Center',
  'bollö skjutfält': 'Bollö övningsfält',
  'falun skjutfält': 'Faluns skjutfält',
  'kungsängens skjutfält': 'Kungsängenfältet',
  'såtenäs skjutfält': 'Såtenäs flygplats - Skaraborgs flygflottilj F 7',
}

/**
 * Mappning av namnlösa GeoJSON-polygoner (osm_id) till GeoJSON-namn.
 * Beräknad via spatial overlap-analys. Dessa polygoner är delar (ways) av
 * namngivna relationer i OSM, men saknar eget "name"-fält i Geofabrik-exporten.
 */
export const OSM_ID_TO_GEO_NAME: Record<string, string> = {
  // Kungsängen
  '766568816': 'Kungsängenfältet',
  // Bodens södra
  '64301921': 'Bodens södra skjutfält',
  '1001540758': 'Bodens södra skjutfält',
  '1093617559': 'Bodens södra skjutfält',
  '1356124003': 'Bodens södra skjutfält',
  '1356124004': 'Bodens södra skjutfält',
  '1356124005': 'Bodens södra skjutfält',
  '1356124006': 'Bodens södra skjutfält',
  // Dagsådalens
  '117434691': 'Dagsådalens skjutfält',
  '117434711': 'Dagsådalens skjutfält',
  // Falun
  '79685080': 'Faluns skjutfält',
  // Härads
  '155008174': 'Härads skjutfält',
  '525237306': 'Härads skjutfält',
  '525237309': 'Härads skjutfält',
  '525237314': 'Härads skjutfält',
  // Horssjön
  '1202921827': 'Horssjöns skjutfält',
  // Prästtomta
  '494628674': 'Prästtomta övnings- och skjutfält',
  '494628675': 'Prästtomta övnings- och skjutfält',
  '494628676': 'Prästtomta övnings- och skjutfält',
  '494628677': 'Prästtomta övnings- och skjutfält',
  // Remmene
  '710474009': 'Remmene skjutfält',
  '710500313': 'Remmene skjutfält',
  // Rosenholm
  '187197901': 'Rosenholms övningsfält',
  '191556272': 'Rosenholms övningsfält',
  '191557529': 'Rosenholms övningsfält',
  '614749512': 'Rosenholms övningsfält',
  // Skillingaryd
  '1218614518': 'Skillingaryds övnings- och skjutfält',
  // Tjurkö
  '14275587': 'Tjurkö övnings- och skjutfält',
  // Tjärnmyran
  '776067415': 'Tjärnmyrans skjutfält',
  // Umeå
  '173526029': 'Umeå övnings- och skjutfält',
  // Utö
  '36361128': 'Utö skjutfält',
  // Villingsbergs
  '5553825': 'Villingsbergs Skjutfält',
  // Vällinge
  '876264120': 'Vällinge övnings- och skjutfält',
  // Älvdalen
  '398496803': 'Älvdalens skjutfält',
  // FMV Karlsborg (Kråk-relaterat)
  '12524887': 'FMV provplats Karlsborg',
}

/**
 * Givet ett FM-fältnamn, returnera GeoJSON-namnet om det finns en mappning.
 * Testar exakt match först, sedan case-insensitive, sedan manuell tabell.
 */
export function fmNameToGeoName(fmName: string, geoNames: Set<string>): string {
  // Exakt match
  if (geoNames.has(fmName)) return fmName

  // Case-insensitive match
  for (const gn of geoNames) {
    if (gn.toLowerCase() === fmName.toLowerCase()) return gn
  }

  // Manuell mappning
  const mapped = FM_TO_GEO[fmName.toLowerCase()]
  if (mapped && geoNames.has(mapped)) return mapped

  return fmName // ingen match, returnera originalet
}

/**
 * Givet ett GeoJSON-namn (från klick på kartan), returnera FM-fältnamnet.
 */
export function geoNameToFmName(geoName: string, fmNames: Set<string>): string {
  // Exakt match
  if (fmNames.has(geoName)) return geoName

  // Case-insensitive match
  for (const fn of fmNames) {
    if (fn.toLowerCase() === geoName.toLowerCase()) return fn
  }

  // Omvänd manuell mappning
  const geoLower = geoName.toLowerCase()
  for (const [fmLower, gn] of Object.entries(FM_TO_GEO)) {
    if (gn.toLowerCase() === geoLower) {
      // Hitta FM-namn med original casing
      for (const fn of fmNames) {
        if (fn.toLowerCase() === fmLower) return fn
      }
    }
  }

  return geoName
}
