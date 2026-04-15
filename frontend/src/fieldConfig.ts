/**
 * Typer och laddning av fältkonfig (field_config.json).
 * Konfigurerar vilka GeoJSON-polygoner (osm_id) som hör till varje FM-fält.
 */
import { dataUrl } from './dataUrl'

export interface FieldConfigEntry {
  osm_ids: string[]
  geo_name: string | null
}

export interface FieldConfig {
  fields: Record<string, FieldConfigEntry>
  permanent_ban_osm_ids?: string[]
}

/**
 * Bygg osm_id → FM-fältnamn-uppslag från konfigurationen.
 */
export function buildOsmIdToFmName(config: FieldConfig): Record<string, string> {
  const map: Record<string, string> = {}
  for (const [fmName, entry] of Object.entries(config.fields)) {
    for (const osmId of entry.osm_ids) {
      map[osmId] = fmName
    }
  }
  return map
}

/**
 * Ladda field_config.json.
 */
export async function loadFieldConfig(): Promise<FieldConfig> {
  const resp = await fetch(dataUrl('field_config.json'))
  return resp.json()
}
