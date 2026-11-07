import { useEffect, useMemo, useState } from 'react'
import MapView from './MapView'
import Search from './Search'
import { AddressCard, BuildingCard, Overview } from './Panels'
import { addressRow, buildingRow } from './format'
import { prefersDark } from './theme'
import './App.css'

const load = (name) => fetch(`${import.meta.env.BASE_URL}data/${name}`).then((r) => r.json())

export default function App() {
  const [theme, setTheme] = useState(prefersDark() ? 'dark' : 'light')
  const [summary, setSummary] = useState(null)
  const [buildings, setBuildings] = useState(null)
  const [validation, setValidation] = useState(null)
  const [addresses, setAddresses] = useState(null)
  const [comps, setComps] = useState({})
  const [layer, setLayer] = useState('values')
  const [selectedId, setSelectedId] = useState(null) // address index
  const [buildingId, setBuildingId] = useState(null)

  useEffect(() => {
    Promise.all([load('summary.json'), load('buildings.json'), load('validation.json')]).then(([s, b, v]) => {
      setSummary(s); setBuildings(b.map(buildingRow)); setValidation(v)
    })
    load('addresses.json').then(setAddresses)
    load('comps.json').then(setComps)
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = (e) => setTheme(e.matches ? 'dark' : 'light')
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  useEffect(() => { document.documentElement.dataset.theme = theme }, [theme])

  // Address indices grouped by building, for the building panel
  const byBuilding = useMemo(() => {
    if (!addresses) return null
    const m = new Map()
    addresses.forEach((r, i) => { const b = r[7]; if (!m.has(b)) m.set(b, []); m.get(b).push(i) })
    return m
  }, [addresses])

  const selected = selectedId != null && addresses ? addressRow(addresses[selectedId]) : null

  const selectAddress = (i) => { setSelectedId(i); setBuildingId(null); setLayer('values') }
  const selectBuilding = (b) => { setBuildingId(b); setSelectedId(null) }
  const back = () => { setSelectedId(null); setBuildingId(null) }

  if (!summary || !buildings) return <div className="loading">Loading ValuIQ…</div>

  return (
    <div className="shell">
      <aside className="side">
        <header className="brand">
          <div>
            <h1>ValuIQ</h1>
            <p>What every City of Sydney flat was worth on 31 August 2026</p>
          </div>
          <button className="ghost" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            aria-label="Toggle light or dark theme">{theme === 'dark' ? 'Light' : 'Dark'}</button>
        </header>
        <Search addresses={addresses} onSelect={selectAddress} />
        <div className="panel">
          {selected ? (
            <AddressCard a={selected} building={buildings[selected.building]} comps={comps[selected.building] || []}
              onBack={back} onBuilding={() => selectBuilding(selected.building)} />
          ) : buildingId != null ? (
            <BuildingCard b={buildings[buildingId]} units={(byBuilding?.get(buildingId) || []).map((i) => [i, addressRow(addresses[i])])}
              comps={comps[buildingId] || []} onBack={back} onSelect={selectAddress} />
          ) : (
            <Overview summary={summary} layer={layer} setLayer={setLayer} theme={theme} />
          )}
        </div>
      </aside>
      <main className="mapwrap">
        <MapView buildings={buildings} validation={validation} breaks={summary.value_breaks} theme={theme}
          layer={layer} selected={selected || (buildingId != null ? buildings[buildingId] : null)} onBuilding={selectBuilding} />
      </main>
    </div>
  )
}
