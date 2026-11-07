import { useEffect, useRef } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { BASEMAP, PALETTE, ERROR_BINS } from './theme'
import { moneyShort } from './format'

const SYDNEY = [151.205, -33.886]

function buildingsGeoJSON(buildings) {
  return {
    type: 'FeatureCollection',
    features: buildings.map((b) => ({
      type: 'Feature', id: b.i,
      geometry: { type: 'Point', coordinates: [b.lng, b.lat] },
      properties: { i: b.i, value: b.value, units: b.units, street: b.street, suburb: b.suburb },
    })),
  }
}

function validationGeoJSON(points) {
  return {
    type: 'FeatureCollection',
    features: points.map(([lat, lng, err, bed]) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [lng, lat] },
      properties: { err, bed, bin: ERROR_BINS.find((b) => b.test(err)).key },
    })),
  }
}

function addLayers(map, { buildings, validation, breaks, theme }) {
  const pal = PALETTE[theme]
  map.addSource('buildings', { type: 'geojson', data: buildingsGeoJSON(buildings) })
  map.addSource('validation', { type: 'geojson', data: validationGeoJSON(validation) })
  map.addSource('selected', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })

  const color = ['step', ['get', 'value'], pal.seq[0]]
  breaks.forEach((b, k) => color.push(b, pal.seq[k + 1]))
  map.addLayer({
    id: 'buildings', type: 'circle', source: 'buildings',
    paint: {
      'circle-color': color,
      'circle-radius': ['interpolate', ['linear'], ['zoom'],
        12, ['interpolate', ['linear'], ['sqrt', ['get', 'units']], 1, 2, 30, 9],
        16, ['interpolate', ['linear'], ['sqrt', ['get', 'units']], 1, 5, 30, 22]],
      'circle-stroke-color': pal.ring,
      'circle-stroke-width': ['case', ['boolean', ['feature-state', 'hover'], false], 2.5, 0.75],
      'circle-opacity': 0.92,
    },
  })
  const div = ['match', ['get', 'bin']]
  Object.entries(pal.div).forEach(([k, c]) => div.push(k, c))
  div.push(pal.div.within)
  map.addLayer({
    id: 'validation', type: 'circle', source: 'validation', layout: { visibility: 'none' },
    paint: {
      'circle-color': div,
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 4, 16, 9],
      'circle-stroke-color': pal.ring, 'circle-stroke-width': 1,
    },
  })
  map.addLayer({
    id: 'selected', type: 'circle', source: 'selected',
    paint: {
      'circle-color': pal.selected, 'circle-radius': 9,
      'circle-stroke-color': pal.ring, 'circle-stroke-width': 3,
    },
  })
}

export default function MapView({ buildings, validation, breaks, theme, layer, selected, onBuilding }) {
  const ref = useRef(null)
  const mapRef = useRef(null)
  const state = useRef({})
  state.current = { buildings, validation, breaks, theme, layer, selected, onBuilding }

  useEffect(() => {
    const map = new maplibregl.Map({
      container: ref.current, style: BASEMAP[theme], center: SYDNEY, zoom: 13.2,
      attributionControl: { compact: true },
    })
    mapRef.current = map
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10, className: 'tip' })
    let hovered = null

    map.on('style.load', () => {
      addLayers(map, state.current)
      applyLayer(map, state.current.layer)
      applySelected(map, state.current.selected)
    })
    map.on('mousemove', 'buildings', (e) => {
      const f = e.features[0]
      if (hovered !== null) map.setFeatureState({ source: 'buildings', id: hovered }, { hover: false })
      hovered = f.id
      map.setFeatureState({ source: 'buildings', id: hovered }, { hover: true })
      map.getCanvas().style.cursor = 'pointer'
      const p = f.properties
      popup.setLngLat(e.lngLat).setHTML(
        `<strong>${p.street}</strong><br>${p.suburb}<br>Median unit <strong>${moneyShort(p.value)}</strong> · ${p.units} units`,
      ).addTo(map)
    })
    map.on('mouseleave', 'buildings', () => {
      if (hovered !== null) map.setFeatureState({ source: 'buildings', id: hovered }, { hover: false })
      hovered = null
      map.getCanvas().style.cursor = ''
      popup.remove()
    })
    map.on('click', 'buildings', (e) => state.current.onBuilding(e.features[0].properties.i))
    map.on('mousemove', 'validation', (e) => {
      const p = e.features[0].properties
      map.getCanvas().style.cursor = 'pointer'
      popup.setLngLat(e.lngLat).setHTML(
        `Valuation error <strong>${p.err > 0 ? '+' : ''}${p.err}%</strong>${p.bed !== 'null' && p.bed != null ? `<br>${p.bed} bed` : ''}`,
      ).addTo(map)
    })
    map.on('mouseleave', 'validation', () => { map.getCanvas().style.cursor = ''; popup.remove() })
    return () => map.remove()
  }, [])

  // Theme change: swap basemap; layers are re-added on style.load
  useEffect(() => {
    const map = mapRef.current
    if (map && map.isStyleLoaded()) map.setStyle(BASEMAP[theme])
  }, [theme])

  useEffect(() => { const m = mapRef.current; if (m && m.getLayer('buildings')) applyLayer(m, layer) }, [layer])

  useEffect(() => {
    const m = mapRef.current
    if (!m) return
    if (m.getSource('selected')) applySelected(m, selected)
    if (selected) m.flyTo({ center: [selected.lng, selected.lat], zoom: Math.max(m.getZoom(), 16.5), speed: 1.4 })
    else m.flyTo({ center: SYDNEY, zoom: 13.2, speed: 1.6 })
  }, [selected?.lat, selected?.lng])

  return <div ref={ref} className="map" role="region" aria-label="Map of City of Sydney flat values" />
}

function applyLayer(map, layer) {
  map.setLayoutProperty('buildings', 'visibility', layer === 'values' ? 'visible' : 'none')
  map.setLayoutProperty('validation', 'visibility', layer === 'accuracy' ? 'visible' : 'none')
}

function applySelected(map, sel) {
  map.getSource('selected').setData({
    type: 'FeatureCollection',
    features: sel ? [{ type: 'Feature', geometry: { type: 'Point', coordinates: [sel.lng, sel.lat] }, properties: {} }] : [],
  })
}
