import { useEffect, useRef } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { FieldStatus } from '../types'
import './Map.css'

interface MapProps {
  statusData: FieldStatus | null
  onFieldClick: (fieldId: string | null) => void
  selectedField: string | null
}

// Sverige centrerat
const SWEDEN_CENTER: [number, number] = [16.5, 62.5]
const SWEDEN_ZOOM = 4.5

export function Map({ statusData, onFieldClick }: MapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const popupRef = useRef<maplibregl.Popup | null>(null)

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
        const feature = e.features[0]
        if (!feature) return

        const props = feature.properties
        const name = props?.name ?? 'Okänt område'
        const osmId = props?.osm_id ?? ''

        onFieldClick(osmId)

        if (popupRef.current) popupRef.current.remove()

        popupRef.current = new maplibregl.Popup({ closeOnClick: true })
          .setLngLat(e.lngLat)
          .setHTML(`<strong>${name}</strong><br/><small>OSM ID: ${osmId}</small>`)
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

  // Uppdatera färger när statusData ändras
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return

    const source = map.getSource('skjutfalt')
    if (!source) return

    // Bygg färguttryck baserat på statusdata
    const colorExpression = buildColorExpression(statusData)
    map.setPaintProperty('skjutfalt-fill', 'fill-color', colorExpression)
  }, [statusData])

  return <div ref={containerRef} className="map-container" />
}

function buildColorExpression(
  statusData: FieldStatus | null,
): maplibregl.ExpressionSpecification {
  if (!statusData || statusData.fields.length === 0) {
    return '#888888'
  }

  const today = new Date().toISOString().split('T')[0]
  const cases: (string | maplibregl.ExpressionSpecification)[] = ['case']

  for (const field of statusData.fields) {
    const hasRestrictionToday = field.restrictions.some(r => r.date === today)
    // Match on name since GeoJSON uses OSM names
    cases.push(
      ['==', ['get', 'name'], field.name],
      hasRestrictionToday ? '#f44336' : '#4CAF50',
    )
  }

  // Default: grå
  cases.push('#888888')
  return cases as maplibregl.ExpressionSpecification
}
