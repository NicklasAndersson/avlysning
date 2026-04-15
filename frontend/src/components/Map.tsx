import { useEffect, useRef, useCallback, useState } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Protocol } from 'pmtiles'
import type { FieldStatus } from '../types'
import type { FieldConfig } from '../fieldConfig'
import { buildOsmIdToFmName, loadFieldConfig } from '../fieldConfig'
import { dataUrl } from '../dataUrl'
import './Map.css'

interface MapProps {
  statusData: FieldStatus | null
  onFieldClick: (fieldId: string | null, permanentBan?: boolean) => void
  selectedField: string | null
  selectedDateTime: Date
}

// PMTiles URL — lokal fil i dev, R2-URL i produktion
const PMTILES_URL = import.meta.env.VITE_PMTILES_URL ?? dataUrl('sweden.pmtiles')

// Sverige centrerat (fallback)
const SWEDEN_CENTER: [number, number] = [16.5, 62.5]
const SWEDEN_ZOOM = 4.5
// Närmare zoom när vi har användarens position
const USER_ZOOM = 8

// Sverige bounding box — visa användarens position bara om den är inom Sverige
const SWEDEN_BOUNDS = { minLon: 10.5, maxLon: 24.2, minLat: 55.0, maxLat: 69.1 }

function isInSweden(lon: number, lat: number): boolean {
  return lon >= SWEDEN_BOUNDS.minLon && lon <= SWEDEN_BOUNDS.maxLon &&
         lat >= SWEDEN_BOUNDS.minLat && lat <= SWEDEN_BOUNDS.maxLat
}

function getUserPosition(): Promise<[number, number] | null> {
  if (!navigator.geolocation) return Promise.resolve(null)
  return new Promise(resolve => {
    navigator.geolocation.getCurrentPosition(
      pos => {
        const { longitude, latitude } = pos.coords
        resolve(isInSweden(longitude, latitude) ? [longitude, latitude] : null)
      },
      () => resolve(null),
      { enableHighAccuracy: false, timeout: 5000, maximumAge: 300_000 }
    )
  })
}

// OpenMapTiles-baserad stil för vektortiles från Tilemaker
function buildBaseStyle(): maplibregl.StyleSpecification {
  return {
    version: 8,
    glyphs: 'https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf',
    sources: {
      openmaptiles: {
        type: 'vector',
        url: `pmtiles://${PMTILES_URL}`,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      },
    },
    layers: [
      // Bakgrund
      {
        id: 'background',
        type: 'background',
        paint: { 'background-color': '#f8f4f0' },
      },
      // Vatten
      {
        id: 'water',
        type: 'fill',
        source: 'openmaptiles',
        'source-layer': 'water',
        paint: { 'fill-color': '#a0c8f0' },
      },
      // Landanvändning
      {
        id: 'landuse-residential',
        type: 'fill',
        source: 'openmaptiles',
        'source-layer': 'landuse',
        filter: ['==', 'class', 'residential'],
        paint: { 'fill-color': '#e8e0d8', 'fill-opacity': 0.7 },
      },
      {
        id: 'landuse-forest',
        type: 'fill',
        source: 'openmaptiles',
        'source-layer': 'landcover',
        filter: ['==', 'class', 'wood'],
        paint: { 'fill-color': '#c8d8c0', 'fill-opacity': 0.6 },
      },
      // Parker
      {
        id: 'park',
        type: 'fill',
        source: 'openmaptiles',
        'source-layer': 'park',
        paint: { 'fill-color': '#d0e8c8', 'fill-opacity': 0.5 },
      },
      // Byggnader
      {
        id: 'building',
        type: 'fill',
        source: 'openmaptiles',
        'source-layer': 'building',
        minzoom: 13,
        paint: { 'fill-color': '#d9d0c9', 'fill-opacity': 0.7 },
      },
      // Vägar — motorvägar
      {
        id: 'road-motorway',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'transportation',
        filter: ['==', 'class', 'motorway'],
        paint: {
          'line-color': '#e0a050',
          'line-width': ['interpolate', ['linear'], ['zoom'], 5, 0.5, 10, 2, 14, 5],
        },
      },
      // Vägar — primär/trunk
      {
        id: 'road-trunk-primary',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'transportation',
        filter: ['in', 'class', 'trunk', 'primary'],
        paint: {
          'line-color': '#d8c870',
          'line-width': ['interpolate', ['linear'], ['zoom'], 7, 0.3, 10, 1.5, 14, 4],
        },
      },
      // Vägar — sekundär
      {
        id: 'road-secondary',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'transportation',
        filter: ['==', 'class', 'secondary'],
        minzoom: 8,
        paint: {
          'line-color': '#e0d8b0',
          'line-width': ['interpolate', ['linear'], ['zoom'], 8, 0.3, 14, 3],
        },
      },
      // Vägar — övriga
      {
        id: 'road-minor',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'transportation',
        filter: ['in', 'class', 'minor', 'service', 'track'],
        minzoom: 11,
        paint: {
          'line-color': '#ffffff',
          'line-width': ['interpolate', ['linear'], ['zoom'], 11, 0.3, 14, 2],
        },
      },
      // Vattendrag
      {
        id: 'waterway',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'waterway',
        paint: {
          'line-color': '#a0c8f0',
          'line-width': ['interpolate', ['linear'], ['zoom'], 8, 0.5, 14, 2],
        },
      },
      // Gränser
      {
        id: 'boundary',
        type: 'line',
        source: 'openmaptiles',
        'source-layer': 'boundary',
        filter: ['<=', 'admin_level', 4],
        paint: {
          'line-color': '#9e9cab',
          'line-width': 1,
          'line-dasharray': [3, 2],
        },
      },
      // Ortnamn
      {
        id: 'place-label',
        type: 'symbol',
        source: 'openmaptiles',
        'source-layer': 'place',
        filter: ['in', 'class', 'city', 'town', 'village'],
        layout: {
          'text-field': ['coalesce', ['get', 'name:sv'], ['get', 'name']],
          'text-font': ['Noto Sans Regular'],
          'text-size': ['interpolate', ['linear'], ['zoom'],
            4, ['match', ['get', 'class'], 'city', 12, 'town', 10, 8],
            10, ['match', ['get', 'class'], 'city', 18, 'town', 14, 12],
          ],
          'text-max-width': 8,
        },
        paint: {
          'text-color': '#333',
          'text-halo-color': 'rgba(255,255,255,0.8)',
          'text-halo-width': 1.5,
        },
      },
    ],
  }
}

export function Map({ statusData, onFieldClick, selectedField, selectedDateTime }: MapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const popupRef = useRef<maplibregl.Popup | null>(null)
  const geojsonRef = useRef<GeoJSON.FeatureCollection | null>(null)
  const configRef = useRef<FieldConfig | null>(null)
  const osmIdToFmNameRef = useRef<Record<string, string>>({})
  const [configLoaded, setConfigLoaded] = useState(false)
  const [mapLoaded, setMapLoaded] = useState(false)

  useEffect(() => {
    if (!containerRef.current) return

    // Registrera PMTiles-protokollet
    const protocol = new Protocol()
    maplibregl.addProtocol('pmtiles', protocol.tile)

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: buildBaseStyle(),
      center: SWEDEN_CENTER,
      zoom: SWEDEN_ZOOM,
    })

    // Flytta kartan till användarens position om den är inom Sverige
    getUserPosition().then(pos => {
      if (pos) map.flyTo({ center: pos, zoom: USER_ZOOM, duration: 1000 })
    })

    // GPS-position
    map.addControl(
      new maplibregl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: true,
      }),
      'top-right'
    )

    map.addControl(new maplibregl.NavigationControl(), 'top-right')

    map.on('load', () => {
      // Ladda skjutfälts-GeoJSON
      map.addSource('skjutfalt', {
        type: 'geojson',
        data: dataUrl('skjutfalt.geojson'),
      })

      // Fyllnadslager
      map.addLayer({
        id: 'skjutfalt-fill',
        type: 'fill',
        source: 'skjutfalt',
        paint: {
          'fill-color': '#888888',
          'fill-opacity': 0.4,
        },
      })

      // Kantlinje
      map.addLayer({
        id: 'skjutfalt-outline',
        type: 'line',
        source: 'skjutfalt',
        paint: {
          'line-color': '#333333',
          'line-width': 1.5,
        },
      })

      // Klick-hantering
      map.on('click', 'skjutfalt-fill', (e) => {
        if (!e.features?.length) return

        // Matcha osm_id → FM-fält via konfigurationen
        let fmName: string | null = null
        let displayName = 'Okänt område'
        for (const feat of e.features) {
          const osmId = String(feat.properties?.osm_id ?? '')
          const resolved = osmIdToFmNameRef.current[osmId]
          if (resolved) {
            fmName = resolved
            displayName = fmName
            break
          }
        }

        // Fallback: visa polygon-namn
        if (!fmName) {
          for (const feat of e.features) {
            const name = feat.properties?.name
            if (name) {
              displayName = name
              break
            }
          }
        }

        console.log('[Polygon click]', {
          fmName,
          displayName,
          allFeatures: e.features.map(f => ({
            osm_id: f.properties?.osm_id,
            name: f.properties?.name,
          })),
        })

        const permanentBanIds = configRef.current?.permanent_ban_osm_ids ?? []
        const clickedOsmIds = e.features.map(f => String(f.properties?.osm_id ?? ''))
        const clickedIsPermanentBan = clickedOsmIds.some(id => permanentBanIds.includes(id))
        onFieldClick(fmName ?? displayName, clickedIsPermanentBan)

        if (popupRef.current) popupRef.current.remove()

        popupRef.current = new maplibregl.Popup({ closeOnClick: true })
          .setLngLat(e.lngLat)
          .setHTML(`<strong>${displayName}</strong>`)
          .addTo(map)
      })

      // Cursor vid hover
      map.on('mouseenter', 'skjutfalt-fill', () => {
        map.getCanvas().style.cursor = 'pointer'
      })
      map.on('mouseleave', 'skjutfalt-fill', () => {
        map.getCanvas().style.cursor = ''
      })

      setMapLoaded(true)
    })

    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
      maplibregl.removeProtocol('pmtiles')
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Ladda GeoJSON och field_config
  useEffect(() => {
    Promise.all([
      fetch(dataUrl('skjutfalt.geojson')).then(r => r.json()),
      loadFieldConfig(),
    ]).then(([geojson, config]: [GeoJSON.FeatureCollection, FieldConfig]) => {
      geojsonRef.current = geojson
      configRef.current = config
      osmIdToFmNameRef.current = buildOsmIdToFmName(config)
      setConfigLoaded(true)
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Uppdatera färger när statusData, config eller vald tid ändras
  useEffect(() => {
    const map = mapRef.current
    if (!map || !mapLoaded || !configLoaded) return

    const source = map.getSource('skjutfalt')
    if (!source) return

    const permanentBanIds = configRef.current?.permanent_ban_osm_ids ?? []
    const colorExpression = buildColorExpression(statusData, osmIdToFmNameRef.current, selectedDateTime, permanentBanIds)
    map.setPaintProperty('skjutfalt-fill', 'fill-color', colorExpression)
  }, [statusData, selectedDateTime, configLoaded, mapLoaded])

  // Flyga till valt fält
  const flyToField = useCallback((fieldName: string) => {
    const map = mapRef.current
    const geojson = geojsonRef.current
    const config = configRef.current
    if (!map || !geojson || !config) return

    const entry = config.fields[fieldName]
    if (!entry || entry.osm_ids.length === 0) return

    // Samla alla koordinater från alla polygoner som tillhör fältet
    const osmIdSet = new Set(entry.osm_ids)
    const allCoords: number[][] = []
    for (const f of geojson.features) {
      const osmId = String((f.properties as Record<string, unknown>)?.osm_id ?? '')
      if (osmIdSet.has(osmId)) {
        allCoords.push(...getAllCoords(f.geometry))
      }
    }
    if (allCoords.length === 0) return

    let minLng = Infinity, maxLng = -Infinity, minLat = Infinity, maxLat = -Infinity
    for (const coord of allCoords) {
      const lng = coord[0]!, lat = coord[1]!
      if (lng < minLng) minLng = lng
      if (lng > maxLng) maxLng = lng
      if (lat < minLat) minLat = lat
      if (lat > maxLat) maxLat = lat
    }

    map.fitBounds(
      [[minLng, minLat], [maxLng, maxLat]],
      { padding: 80, maxZoom: 13, duration: 1500 }
    )
  }, [])

  useEffect(() => {
    if (selectedField) {
      flyToField(selectedField)
    }
  }, [selectedField, flyToField])

  return <div ref={containerRef} className="map-container" />
}

function getAllCoords(geometry: GeoJSON.Geometry): number[][] {
  switch (geometry.type) {
    case 'Polygon':
      return geometry.coordinates.flat()
    case 'MultiPolygon':
      return geometry.coordinates.flat(2)
    case 'Point':
      return [geometry.coordinates]
    case 'LineString':
      return geometry.coordinates
    default:
      return []
  }
}

function formatDateISO(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function formatTimeHHMM(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function isRestrictionActiveAt(r: { date: string; start?: string; end?: string }, dt: Date): boolean {
  if (r.date !== formatDateISO(dt)) return false
  // Om start/end saknas → heldag
  if (!r.start || !r.end) return true
  const timeStr = formatTimeHHMM(dt)
  return timeStr >= r.start && timeStr < r.end
}

function buildColorExpression(
  statusData: FieldStatus | null,
  osmIdToFmName: Record<string, string>,
  selectedDateTime: Date,
  permanentBanIds: string[],
): maplibregl.ExpressionSpecification {
  const cases: (string | maplibregl.ExpressionSpecification)[] = ['case']

  // Permanenta tillträdesförbud (garnisoner, örlogsbaser etc.) — alltid svart
  for (const osmId of permanentBanIds) {
    cases.push(
      ['==', ['get', 'osm_id'], osmId],
      '#1a1a1a',
    )
  }

  if (!statusData || statusData.fields.length === 0) {
    cases.push('#888888')
    if (cases.length === 2) {
      return '#888888' as unknown as maplibregl.ExpressionSpecification
    }
    return cases as maplibregl.ExpressionSpecification
  }

  const selectedDate = formatDateISO(selectedDateTime)

  // Bygg klassificering per FM-fält
  const fmNameColor: Record<string, string> = {}
  for (const field of statusData.fields) {
    const dateRestrictions = field.restrictions.filter(r => r.date === selectedDate)
    const activeRestrictions = field.restrictions.filter(r => isRestrictionActiveAt(r, selectedDateTime))

    if (activeRestrictions.length > 0) {
      // Aktiv just nu — röd (permanenta hanteras via permanent_ban_osm_ids)
      fmNameColor[field.name] = '#f44336'
    } else if (dateRestrictions.length > 0) {
      // Restriktion denna dag men inte just nu — gul
      fmNameColor[field.name] = '#FFC107'
    } else {
      fmNameColor[field.name] = '#4CAF50'  // Grön: inga restriktioner denna dag
    }
  }

  // Färglägg varje osm_id baserat på dess FM-fält
  for (const [osmId, fmName] of Object.entries(osmIdToFmName)) {
    const color = fmNameColor[fmName]
    if (color) {
      cases.push(
        ['==', ['get', 'osm_id'], osmId],
        color,
      )
    }
  }

  // Default: grå (okänt/ej mappat fält)
  cases.push('#888888')

  // Om inga case-villkor lades till, returnera bara defaultfärgen
  if (cases.length === 2) {
    return '#888888' as unknown as maplibregl.ExpressionSpecification
  }

  return cases as maplibregl.ExpressionSpecification
}
