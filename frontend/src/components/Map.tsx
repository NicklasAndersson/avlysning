import { useEffect, useRef } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { FieldStatus } from '../types'
import { geoNameToFmName, fmNameToGeoName } from '../nameMapping'
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
  const fmNamesRef = useRef<Set<string>>(new Set())
  const geoNamesRef = useRef<Set<string>>(new Set())

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
        const geoName = props?.name ?? 'Okänt område'
        const fmName = geoNameToFmName(geoName, fmNamesRef.current)

        onFieldClick(fmName)

        if (popupRef.current) popupRef.current.remove()

        popupRef.current = new maplibregl.Popup({ closeOnClick: true })
          .setLngLat(e.lngLat)
          .setHTML(`<strong>${name}</strong>`)
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

  // Ladda GeoJSON-namn en gång när kartan laddats
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const onIdle = () => {
      const source = map.getSource('skjutfalt') as maplibregl.GeoJSONSource | undefined
      if (!source) return
      const features = map.querySourceFeatures('skjutfalt')
      const names = new Set<string>()
      for (const f of features) {
        const n = f.properties?.name
        if (n) names.add(n)
      }
      geoNamesRef.current = names
    }
    map.on('idle', onIdle)
    return () => { map.off('idle', onIdle) }
  }, [])

  // Uppdatera färger när statusData ändras
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return

    const source = map.getSource('skjutfalt')
    if (!source) return

    // Uppdatera FM-namn ref
    if (statusData) {
      fmNamesRef.current = new Set(statusData.fields.map(f => f.name))
    }

    // Bygg färguttryck baserat på statusdata
    const colorExpression = buildColorExpression(statusData, geoNamesRef.current)
    map.setPaintProperty('skjutfalt-fill', 'fill-color', colorExpression)
  }, [statusData])

  return <div ref={containerRef} className="map-container" />
}

function buildColorExpression(
  statusData: FieldStatus | null,
  geoNames: Set<string>,
): maplibregl.ExpressionSpecification {
  if (!statusData || statusData.fields.length === 0) {
    return '#888888'
  }

  const today = new Date().toISOString().split('T')[0]
  const cases: (string | maplibregl.ExpressionSpecification)[] = ['case']

  // Bygg set av GeoJSON-namn med aktiva restriktioner idag
  const activeGeoNames = new Set<string>()
  const knownGeoNames = new Set<string>()
  for (const field of statusData.fields) {
    const geoName = fmNameToGeoName(field.name, geoNames)
    knownGeoNames.add(geoName)
    if (field.restrictions.some(r => r.date === today)) {
      activeGeoNames.add(geoName)
    }
  }

  for (const geoName of knownGeoNames) {
    cases.push(
      ['==', ['get', 'name'], geoName],
      activeGeoNames.has(geoName) ? '#f44336' : '#4CAF50',
    )
  }

  // Default: grå
  cases.push('#888888')
  return cases as maplibregl.ExpressionSpecification
}
