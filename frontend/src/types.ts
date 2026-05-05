export interface Restriction {
  date: string
  start?: string
  end?: string
  type: string
  sectors: string[]
  source_url?: string
}

export interface Field {
  id: string
  name: string
  source: string
  source_url?: string
  pdf_urls?: string[]
  restrictions: Restriction[]
  /** PDF-URLer som inte kunde parsas (tomma/oläsbara även efter OCR). */
  parse_errors?: string[]
}

export interface FieldStatus {
  last_updated: string
  fields: Field[]
}
