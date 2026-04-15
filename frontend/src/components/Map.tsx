import { useEffect, useRef, useCallback } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { FieldStatus } from '../types'
import { geoNameToFmName, fmNameToGeoName, OSM_ID_TO_GEO_NAME } from '../nameMapping'
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
  const fmNamesRef = useRef<Set<string>>(new Set())
  const geoNamesRef = useRef<Set<string>>(new Set())
  const geojsonRef = useRef<GeoJSON.FeatureCollection | null>(null)

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

        // Prefer a feature with a name (nameless polygons are often parts of named relations)
        const namedFeature = e.features.find(f => f.properties?.name)
        const feature = namedFeature ?? e.features[0]!

        const props = feature.properties
        // Resolve name: direct name → osm_id lookup → 'Okänt område'
        const geoName = props?.name
          ?? OSM_ID_TO_GEO_NAME[String(props?.osm_id)]
          ?? 'Okänt område'
        const fmName = geoNameToFmName(geoName, fmNamesRef.current)

        console.log('[Polygon click]', {
          geoName,
          fmName,
          allFeatures: e.features.map(f => f.properties),
          matched: fmNamesRef.current.has(fmName),
          geoNamesLoaded: geoNamesRef.current.size,
        })

        onFieldClick(fmName)

        if (popupRef.current) popupRef.current.remove()

        popupRef.current = new maplibregl.Popup({ closeOnClick: true })
          .setLngLat(e.lngLat)
          .setHTML(`<strong>${geoName}</strong>`)
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

  // Ladda alla GeoJSON-namn direkt från filen (ej querySourceFeatures som saknar icke-synliga)
  useEffect(() => {
    fetch('/data/skjutfalt.geojson')
      .then(r => r.json())
      .then((geojson: GeoJSON.FeatureCollection) => {
        geojsonRef.current = geojson
        const names = new Set<string>()
        for (const f of geojson.features) {
          const n = (f.properties as Record<string, unknown>)?.name
          if (typeof n === 'string') names.add(n)
        }
        geoNamesRef.current = names
        // Re-trigger coloring now that geoNames is populated
        if (mapRef.current && statusData) {
          const expr = buildColorExpression(statusData, names)
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

    // Uppdatera FM-namn ref
    if (statusData) {
      fmNamesRef.current = new Set(statusData.fields.map(f => f.name))
    }

    // Bygg färguttryck baserat på statusdata
    const colorExpression = buildColorExpression(statusData, geoNamesRef.current)
    map.setPaintProperty('skjutfalt-fill', 'fill-color', colorExpression)
  }, [statusData])

  // Flyga till valt fält när det väljs från listan
  const flyToField = useCallback((fieldName: string) => {
    const map = mapRef.current
    const geojson = geojsonRef.current
    if (!map || !geojson) return

    const geoName = fmNameToGeoName(fieldName, geoNamesRef.current)

    // Hitta feature med matchande namn
    const feature = geojson.features.find(
      f => (f.properties as Record<string, unknown>)?.name === geoName
    )
    if (!feature) return

    // Beräkna bbox
    const coords = getAllCoords(feature.geometry)
    if (coords.length === 0) return

    let minLng = Infinity, maxLng = -Infinity, minLat = Infinity, maxLat = -Infinity
    for (const [lng, lat] of coords) {
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
  geoNames: Set<string>,
): maplibregl.ExpressionSpecification {
  if (!statusData || statusData.fields.length === 0) {
    return '#888888'
  }

  const today = new Date().toLocaleDateString('sv-SE')
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

  // Färglägg namngivna polygoner via name-property
  for (const geoName of knownGeoNames) {
    cases.push(
      ['==', ['get', 'name'], geoName],
      activeGeoNames.has(geoName) ? '#f44336' : '#4CAF50',
    )
  }

  // Färglägg namnlösa polygoner via osm_id → geoName-mappning
  for (const [osmId, geoName] of Object.entries(OSM_ID_TO_GEO_NAME)) {
    if (knownGeoNames.has(geoName)) {
      cases.push(
        ['==', ['get', 'osm_id'], Number(osmId)],
        activeGeoNames.has(geoName) ? '#f44336' : '#4CAF50',
      )
    }
  }

  // Default: grå
  cases.push('#888888')
  return cases as maplibregl.ExpressionSpecification
}
