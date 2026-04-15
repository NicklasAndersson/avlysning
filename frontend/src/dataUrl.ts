// Base-URL för dataresurser: lokal sökväg i dev, R2 i produktion
const DATA_BASE_URL = import.meta.env.VITE_DATA_BASE_URL ?? '/data'

export function dataUrl(path: string): string {
  return `${DATA_BASE_URL}/${path}`
}
