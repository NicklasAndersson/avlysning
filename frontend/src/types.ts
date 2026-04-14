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
  restrictions: Restriction[]
}

export interface FieldStatus {
  last_updated: string
  fields: Field[]
}
