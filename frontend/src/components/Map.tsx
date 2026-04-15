import { useEffect, useRef, useCallback } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { FieldStatus } from '../types'
import type { FieldConfig } from '../fieldConfig'
import { buildOsmIdToFmName, loadFieldConfig } from '../fieldConfig'
import './Map.css'

interface MapProps {
  statusData: FieldStatus | null
  onFieldClick: (fieldId: string | null) => void
  selectedField: string | null
}

// Sverige centrerat
const SWEDEN_CENTER: [number, number] = [16.5, 62.5]
const SWEDEN_ZOOM = 4.5

export function Map({ statusData, onFieldClick, selectedField }: MapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const popupRef = useRef<maplibregl.Popup | null>(null)
  const geojsonRef = useRef<GeoJSON.FeatureCollection | null>(null)
  const configRef = useRef<FieldConfig | null>(null)
  const osmIdToFmNameRef = useRef<Record<string, string>>({})

  useEffect(() => {
    if (!containerRef.current) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
          },
        },
        layers: [
          {
            id: 'osm-tiles',
            type: 'raster',
            source: 'osm',
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: SWEDEN_CENTER,
      zoom: SWEDEN_ZOOM,
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
        data: '/data/skjutfalt.geojson',
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

        onFieldClick(fmName ?? displayName)

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
    })

    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Ladda GeoJSON och field_config
  useEffect(() => {
    Promise.all([
      fetch('/data/skjutfalt.geojson').then(r => r.json()),
      loadFieldConfig(),
    ]).then(([geojson, config]: [GeoJSON.FeatureCollection, FieldConfig]) => {
      geojsonRef.current = geojson
      configRef.current = config
      osmIdToFmNameRef.current = buildOsmIdToFmName(config)

      // Trigger färgläggning om statusData redan finns
      if (mapRef.current && statusData) {
        const expr = buildColorExpression(statusData, osmIdToFmNameRef.current)
        mapRef.current.setPaintProperty('skjutfalt-fill', 'fill-color', expr)
      }
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Uppdatera färger när statusData ändras
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return

    const source = map.getSource('skjutfalt')
    if (!source) return

    const colorExpression = buildColorExpression(statusData, osmIdToFmNameRef.current)
    map.setPaintProperty('skjutfalt-fill', 'fill-color', colorExpression)
  }, [statusData])

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

function buildColorExpression(
  statusData: FieldStatus | null,
  osmIdToFmName: Record<string, string>,
): maplibregl.ExpressionSpecification {
  if (!statusData || statusData.fields.length === 0) {
    return '#888888' as unknown as maplibregl.ExpressionSpecification
  }

  const today = new Date().toLocaleDateString('sv-SE')
  const cases: (string | maplibregl.ExpressionSpecification)[] = ['case']

  // Bygg set av FM-fältnamn med aktiva restriktioner idag
  const activeFmNames = new Set<string>()
  const fmNameSet = new Set<string>()
  for (const field of statusData.fields) {
    fmNameSet.add(field.name)
    if (field.restrictions.some(r => r.date === today)) {
      activeFmNames.add(field.name)
    }
  }

  // Färglägg varje osm_id baserat på dess FM-fält
  for (const [osmId, fmName] of Object.entries(osmIdToFmName)) {
    if (fmNameSet.has(fmName)) {
      cases.push(
        ['==', ['get', 'osm_id'], osmId],
        activeFmNames.has(fmName) ? '#f44336' : '#4CAF50',
      )
    }
  }

  // Default: grå
  cases.push('#888888')
  return cases as maplibregl.ExpressionSpecification
}
