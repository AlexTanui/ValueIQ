import { useState } from 'react'
import { money, moneyShort, pct } from './format'
import { PALETTE, ERROR_BINS } from './theme'

function Stat({ k, v, d, good }) {
  return (
    <div className="stat">
      <div className="k">{k}</div>
      <div className="v">{v}</div>
      {d && <div className={`d ${good ? 'good' : ''}`}>{d}</div>}
    </div>
  )
}

export function Overview({ summary, layer, setLayer, theme }) {
  const h = summary.headline
  const pal = PALETTE[theme]
  const best = 109 / 227
  return (
    <>
      <div className="seg" role="tablist" aria-label="Map layer">
        <button role="tab" aria-selected={layer === 'values'} className={layer === 'values' ? 'on' : ''}
          onClick={() => setLayer('values')}>Predicted values</button>
        <button role="tab" aria-selected={layer === 'accuracy'} className={layer === 'accuracy' ? 'on' : ''}
          onClick={() => setLayer('accuracy')}>Model accuracy</button>
      </div>

      {layer === 'values' ? (
        <section>
          <p className="lede">Each dot is a building, coloured by the median value of its units and sized by unit count. Click a building or search for an address.</p>
          <div className="legend">
            {pal.seq.map((c, i) => {
              const lo = i === 0 ? null : summary.value_breaks[i - 1]
              const hi = summary.value_breaks[i]
              return (
                <span key={c}><i style={{ background: c }} />
                  {lo == null ? `under ${moneyShort(hi)}` : hi == null ? `${moneyShort(lo)}+` : `${moneyShort(lo)}–${moneyShort(hi)}`}
                </span>
              )
            })}
          </div>
        </section>
      ) : (
        <section>
          <p className="lede">Confirmed flat sales from July–August 2026, valued using only information from before 1 July. Each dot shows the error as a percentage.</p>
          <div className="legend">
            {ERROR_BINS.map((b) => <span key={b.key}><i style={{ background: pal.div[b.key] }} />{b.label}</span>)}
          </div>
        </section>
      )}

      <div className="stats">
        <Stat k="Within 10% (holdout, <$1.2M)" v={pct(h.within10)} d={`+${Math.round((h.within10 - best) * 100)} pts on best organiser result`} good />
        <Stat k="Median absolute error" v={moneyShort(h.mdae)} d="holdout, under $1.2M" />
        <Stat k="R² held-out" v={h.r2.toFixed(2)} d={`${h.n_val} Jul–Aug 2026 sales`} />
        <Stat k="Addresses valued" v={h.n_addresses.toLocaleString('en-AU')} d={`${h.missing} missing`} />
      </div>

      <section>
        <h3>Share of sales valued within 10%</h3>
        <Bars rows={summary.comparison} />
        <p className="note">ValuIQ rows: Jul–Aug 2026 holdout ({h.n_val_u12} sales under $1.2M). Organiser rows: task brief, 227 private Sep–Nov 2026 sales. These are indicative, not a like-for-like comparison.</p>
      </section>

      <section>
        <h3>Unit price index (Aug 2026 = 1.00)</h3>
        <IndexChart index={summary.index} />
        <p className="note">Repeat-sales index built only from sales up to 31 Aug 2026. It brings every past sale to today's prices.</p>
      </section>
    </>
  )
}

function Bars({ rows }) {
  return (
    <div className="bars">
      {rows.map((r) => (
        <div key={r.label} className={`bar-row ${r.ours ? 'ours' : ''}`} title={`${r.label}: ${pct(r.value)}`}>
          <span className="lab">{r.label}</span>
          <span className="track"><span style={{ width: `${(r.value / 0.8) * 100}%` }} /></span>
          <span className="num">{pct(r.value, 0)}</span>
        </div>
      ))}
    </div>
  )
}

function IndexChart({ index }) {
  const [hover, setHover] = useState(null)
  const { labels, values } = index
  const W = 360, H = 130, L = 30, R = 8, T = 8, B = 20
  const min = Math.floor(Math.min(...values) * 10) / 10, max = Math.ceil(Math.max(...values) * 10) / 10
  const n = values.length - 1
  const x = (i) => L + ((W - L - R) * i) / n
  const y = (v) => T + (H - T - B) * (1 - (v - min) / (max - min))
  const ticks = []
  for (let v = min; v <= max + 1e-9; v += 0.2) ticks.push(+v.toFixed(1))
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Quarterly unit price index"
        onMouseMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect()
          const i = Math.round((((e.clientX - r.left) * W) / r.width - L) / (W - L - R) * n)
          setHover(Math.max(0, Math.min(n, i)))
        }}
        onMouseLeave={() => setHover(null)}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} className="grid" />
            <text x={L - 6} y={y(t) + 3} textAnchor="end" className="tick">{t.toFixed(1)}</text>
          </g>
        ))}
        {labels.map((l, i) => l.endsWith('Q1') && +l.slice(0, 4) % 5 === 0 &&
          <text key={l} x={x(i)} y={H - 4} textAnchor="middle" className="tick">{l.slice(0, 4)}</text>)}
        <path d={values.map((v, i) => `${i ? 'L' : 'M'}${x(i)},${y(v)}`).join('')} className="line" />
        {hover != null && (
          <g>
            <line x1={x(hover)} x2={x(hover)} y1={T} y2={H - B} className="cross" />
            <circle cx={x(hover)} cy={y(values[hover])} r="4" className="dot" />
            <text x={Math.min(x(hover) + 6, W - 90)} y={T + 10} className="hover">{labels[hover]}: {values[hover].toFixed(2)}</text>
          </g>
        )}
      </svg>
    </div>
  )
}

export function AddressCard({ a, building, comps, onBack, onBuilding }) {
  const ev = [
    ['Own last sale', a.ownYears != null ? `sold ${a.ownYears} yrs ago, indexed to Aug 2026` : 'no earlier sale on record', a.own],
    ['Same building', a.bldbedN ? `${a.bldbedN} similar unit sale${a.bldbedN === 1 ? '' : 's'}, indexed` : 'no similar sales on record', a.bldbed],
    ['Nearby sales', 'closest sales in the last 2 years, distance-weighted', a.nbr],
  ]
  const max = Math.max(a.value, ...ev.map((e) => e[2] || 0)) * 1.05
  const chips = [a.bed != null ? `${a.bed} bed` : 'bedrooms unknown', a.bath != null && `${a.bath} bath`,
    a.car != null && `${a.car} car`, a.floor != null && `floor ${a.floor}`, `${building.units} units in building`,
    a.commercial && 'shop / office / suite'].filter(Boolean)
  return (
    <section className="card-in">
      <button className="link" onClick={onBack}>← Overview</button>
      <h2>{a.address}</h2>
      <p className="muted">{a.suburb}</p>
      <div className="k">Estimated value at 31 August 2026</div>
      <div className="big">{money(a.value)}</div>
      <div className="muted">Within-10% band {money(a.value * 0.9)} – {money(a.value * 1.1)}</div>
      <div className="chips">{chips.map((c) => <span key={c}>{c}</span>)}</div>

      <h3>Evidence behind the value</h3>
      {ev.map(([l, s, v]) => (
        <div className="ev" key={l}>
          <div className="lab">{l}<small>{s}</small></div>
          <div className="track">{v ? <span style={{ width: `${(v / max) * 100}%` }} /> : null}</div>
          <div className="num">{moneyShort(v)}</div>
        </div>
      ))}
      <div className="ev final">
        <div className="lab"><strong>ValuIQ value</strong><small>LightGBM weighs all the evidence</small></div>
        <div className="track"><span style={{ width: `${(a.value / max) * 100}%` }} /></div>
        <div className="num"><strong>{moneyShort(a.value)}</strong></div>
      </div>

      <h3>Recent sales in this building <button className="link small" onClick={onBuilding}>see all units →</button></h3>
      <CompTable comps={comps} />
      <p className="note">G-NAF {a.id}. Only sales up to 31 Aug 2026 are used.</p>
    </section>
  )
}

function CompTable({ comps }) {
  if (!comps.length) return <p className="muted">No recorded sales in this building before 31 Aug 2026.</p>
  return (
    <table>
      <thead><tr><th>Unit</th><th>Sold</th><th>Beds</th><th>Price</th><th>Aug 2026 $</th></tr></thead>
      <tbody>
        {comps.map(([u, d, p, t, b], k) => (
          <tr key={k}><td>{u}</td><td>{d}</td><td>{b ?? '–'}</td><td>{moneyShort(p)}</td><td>{moneyShort(t)}</td></tr>
        ))}
      </tbody>
    </table>
  )
}

export function BuildingCard({ b, units, comps, onBack, onSelect }) {
  const sorted = units.slice().sort((x, y) => (x[1].floor ?? 0) - (y[1].floor ?? 0) || x[1].address.localeCompare(y[1].address, 'en', { numeric: true }))
  return (
    <section className="card-in">
      <button className="link" onClick={onBack}>← Overview</button>
      <h2>{b.street}</h2>
      <p className="muted">{b.suburb}</p>
      <div className="stats two">
        <Stat k="Median unit value" v={moneyShort(b.value)} />
        <Stat k="Units" v={b.units} d={b.floors ? `up to floor ${b.floors}` : null} />
      </div>
      <h3>Recent sales</h3>
      <CompTable comps={comps} />
      <h3>Units ({units.length})</h3>
      <ul className="units">
        {sorted.map(([i, u]) => (
          <li key={i}><button onClick={() => onSelect(i)}>
            <span>{u.address.split(',')[0]}<small>{[u.bed != null && `${u.bed} bed`, u.floor != null && `floor ${u.floor}`].filter(Boolean).join(' · ')}</small></span>
            <b>{moneyShort(u.value)}</b>
          </button></li>
        ))}
      </ul>
    </section>
  )
}
