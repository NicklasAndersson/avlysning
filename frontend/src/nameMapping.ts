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
