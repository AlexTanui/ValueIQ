import { useMemo, useState } from 'react'
import { moneyShort } from './format'

export default function Search({ addresses, onSelect }) {
  const [q, setQ] = useState('')
  const [sel, setSel] = useState(0)
  const [open, setOpen] = useState(false)

  const index = useMemo(() => addresses?.map((r) => `${r[1]} ${r[2]}`.toLowerCase().replace(/,/g, '')), [addresses])

  const hits = useMemo(() => {
    const terms = q.toLowerCase().replace(/,/g, ' ').split(/\s+/).filter(Boolean)
    if (!index || !terms.length) return []
    const out = []
    for (let i = 0; i < index.length && out.length < 8; i++) if (terms.every((t) => index[i].includes(t))) out.push(i)
    return out
  }, [q, index])

  const choose = (i) => { onSelect(i); setQ(`${addresses[i][1]}, ${addresses[i][2]}`); setOpen(false) }

  return (
    <div className="search">
      <input
        value={q}
        placeholder={addresses ? 'Search any address, e.g. 3 Earl Place' : 'Loading 181,711 addresses…'}
        disabled={!addresses}
        aria-label="Search for an address"
        onChange={(e) => { setQ(e.target.value); setSel(0); setOpen(true) }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') { setSel(Math.min(sel + 1, hits.length - 1)); e.preventDefault() }
          if (e.key === 'ArrowUp') { setSel(Math.max(sel - 1, 0)); e.preventDefault() }
          if (e.key === 'Enter' && hits.length) choose(hits[sel])
          if (e.key === 'Escape') setOpen(false)
        }}
      />
      {open && hits.length > 0 && (
        <ul className="sugg" role="listbox">
          {hits.map((i, j) => (
            <li key={i} role="option" aria-selected={j === sel} className={j === sel ? 'on' : ''}
              onMouseDown={() => choose(i)} onMouseEnter={() => setSel(j)}>
              <span>{addresses[i][1]}<small>{addresses[i][2]}</small></span>
              <b>{moneyShort(addresses[i][3])}</b>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
