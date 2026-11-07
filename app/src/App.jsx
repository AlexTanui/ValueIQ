import { useEffect, useMemo, useState } from 'react'
import MapView from './MapView'
import Search from './Search'
import Assistant from './Assistant.jsx'
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
  const [lifestyle, setLifestyle] = useState(null)
  const [chat, setChat] = useState([])
  const [recs, setRecs] = useState([])

  useEffect(() => {
    Promise.all([load('summary.json'), load('buildings.json'), load('validation.json')]).then(([s, b, v]) => {
      setSummary(s); setBuildings(b.map(buildingRow)); setValidation(v)
    })
    load('addresses.json').then(setAddresses)
    load('comps.json').then(setComps)
    load('lifestyle.json').then(setLifestyle).catch(() => setLifestyle(null))
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

  const selectAddress = (i) => { setSelectedId(i); setBuildingId(null); if (layer === 'accuracy') setLayer('values') }
  const showRecs = (r) => {
    const pin = (i, rank, stretch) => {
      const a = addresses[i]
      return { i, rank, stretch, lat: a[8], lng: a[9], address: a[1], suburb: a[2], value: a[3] }
    }
    setRecs([...r.results.map((i, k) => pin(i, k + 1, false)), ...r.closest.map((i, k) => pin(i, r.results.length + k + 1, true))])
  }
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
              onBack={back} onBuilding={() => selectBuilding(selected.building)}
              forecast={lifestyle?.suburbs?.[selected.suburb]?.forecast_unit_1y} growth={summary.growth} />
          ) : buildingId != null ? (
            <BuildingCard b={buildings[buildingId]} units={(byBuilding?.get(buildingId) || []).map((i) => [i, addressRow(addresses[i])])}
              comps={comps[buildingId] || []} onBack={back} onSelect={selectAddress} />
          ) : (
            <>
              <div className="seg three" role="tablist" aria-label="Mode">
                {[['values', 'Values'], ['accuracy', 'Accuracy'], ['ask', 'Ask ValuIQ']].map(([k, l]) => (
                  <button key={k} role="tab" aria-selected={layer === k} className={layer === k ? 'on' : ''} onClick={() => setLayer(k)}>{l}</button>
                ))}
              </div>
              {layer === 'ask'
                ? <Assistant addresses={addresses} lifestyle={lifestyle} chat={chat} setChat={setChat} onResults={showRecs} onSelect={selectAddress} />
                : <Overview summary={summary} layer={layer} theme={theme} />}
            </>
          )}
        </div>
      </aside>
      <main className="mapwrap">
        <MapView buildings={buildings} validation={validation} breaks={summary.value_breaks} theme={theme}
          layer={layer} selected={selected || (buildingId != null ? buildings[buildingId] : null)} onBuilding={selectBuilding}
          recs={recs} onRec={selectAddress} />
      </main>
    </div>
  )
}
