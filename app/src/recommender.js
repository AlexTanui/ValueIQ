// ValuIQ assistant: turns a plain-English question into filters and preferences,
// then ranks supplied addresses by ValuIQ value, bedrooms and current suburb
// lifestyle data. Rule-based, runs entirely in the browser.
//
// Lifestyle data (crime, livability, income, rent) is CURRENT API data and is used
// here only for recommendations, never as a valuation feature.

import { moneyShort } from './format.js'

const INCOME_MULTIPLE = 6 // rule of thumb: price ≈ 6× gross income (about 5× borrowing plus a 20% deposit)

const PREFS = [
  { key: 'safety', words: ['safe', 'safety', 'low crime', 'secure', 'crime'], label: 'safety' },
  { key: 'family', words: ['family', 'kids', 'children', 'school'], label: 'family-friendly' },
  { key: 'tranquility', words: ['quiet', 'peaceful', 'calm', 'tranquil'], label: 'quiet' },
  { key: 'hip', words: ['nightlife', 'hip', 'vibrant', 'trendy', 'bars', 'young'], label: 'vibrant' },
  { key: 'lifestyle', words: ['lifestyle', 'cafe', 'cafes', 'restaurants', 'dining'], label: 'lifestyle' },
  { key: 'convenience', words: ['convenient', 'convenience', 'shops', 'shopping', 'walkable'], label: 'convenient' },
  { key: 'station', words: ['train', 'station', 'metro', 'transport', 'commute', 'light rail'], label: 'near a station' },
  { key: 'water', words: ['water', 'harbour', 'harbor', 'bay', 'waterfront', 'view'], label: 'near the water' },
]

const NUMBER_WORDS = { studio: 0, one: 1, two: 2, three: 3, four: 4 }

function toDollars(num, suffix) {
  let v = parseFloat(num.replace(/,/g, ''))
  if (/^(k|thousand)/.test(suffix)) v *= 1e3
  else if (/^(m|mil|million)/.test(suffix)) v *= 1e6
  else if (v < 5000) v *= 1e3 // "600" in a property question almost always means $600k
  return v
}

export function parseQuery(text, suburbNames) {
  const t = ' ' + text.toLowerCase().replace(/[–—]/g, '-') + ' '
  const q = { income: null, budget: null, bed: null, bath: null, car: false, prefs: [], suburbs: [] }

  const bed = t.match(/\b(\d|one|two|three|four|studio)[\s-]*(?:bed(?:room)?s?|br\b|b\/r)/) || t.match(/\bstudio\b/)
  if (bed) q.bed = bed[1] in NUMBER_WORDS ? NUMBER_WORDS[bed[1]] : bed[1] ? +bed[1] : 0
  const bath = t.match(/\b(\d|one|two|three)[\s-]*bath/)
  if (bath) q.bath = bath[1] in NUMBER_WORDS ? NUMBER_WORDS[bath[1]] : +bath[1]
  q.car = /\b(parking|car ?space|car ?spot|garage)\b/.test(t)

  const money = /\$?\s*(\d[\d,]*(?:\.\d+)?)\s*(k\b|thousand|m\b|mil|million)?/g
  let m
  while ((m = money.exec(t))) {
    const after = t.slice(m.index + m[0].length, m.index + m[0].length + 18)
    if (/^\s*[-\s]*(bed|bath|br\b|car)/.test(after)) continue
    if (!m[2] && !m[0].includes('$') && +m[1].replace(/,/g, '') < 50) continue // small bare numbers aren't money
    const before = t.slice(Math.max(0, m.index - 30), m.index)
    const v = toDollars(m[1], m[2] || '')
    if (/(earn|earning|income|salary|make|making|paid|on)\s*\$?\s*$/.test(before) || /^\s*(per|a|p\.?a|\/)\s*(year|yr|annum|annual)?/.test(after) && /(per|a) (year|yr)|p\.?a|annum/.test(after)) q.income = v
    else if (/(under|below|less than|max|maximum|budget|up to|afford|within|cheaper than|at most)\s*(of\s*)?\$?\s*$/.test(before)) q.budget = v
    else if (q.income == null && v < 400_000 && /earn|income|salary/.test(t)) q.income = v
    else if (q.budget == null && v >= 150_000) q.budget = v
  }

  for (const p of PREFS) if (p.words.some((w) => t.includes(w))) q.prefs.push(p.key)
  for (const name of suburbNames) {
    const bare = name.replace(/\s*\(.*\)$/, '').toLowerCase()
    if (bare.length > 3 && new RegExp(`\\b${bare}\\b`).test(t) && bare !== 'sydney') q.suburbs.push(name)
  }
  if (/\b(sydney cbd|the cbd|city centre)\b/.test(t)) q.suburbs.push('Sydney')
  return q
}

function percentileRank(values) {
  const sorted = values.filter((v) => v != null).sort((a, b) => a - b)
  return (v) => (v == null ? null : sorted.findIndex((s) => s >= v) / Math.max(1, sorted.length - 1))
}

export function recommend(q, addresses, lifestyle, limit = 25) {
  const subs = lifestyle.suburbs
  const scoreRank = {}
  for (const key of ['safety', 'family', 'tranquility', 'hip', 'lifestyle', 'convenience']) {
    scoreRank[key] = percentileRank(Object.values(subs).map((s) => s.scores?.[key]))
  }
  const crimeRank = percentileRank(Object.values(lifestyle.mb_crime))
  const incomeBudget = q.income ? q.income * INCOME_MULTIPLE : null
  const budget = q.budget ?? incomeBudget

  const base = (strictSafety) => {
    const out = []
    for (let i = 0; i < addresses.length; i++) {
      const r = addresses[i]
      if (r[16] || r[20] || !r[3]) continue // commercial, car space, no value
      if (q.bed != null && r[4] !== q.bed) continue
      if (q.bath != null && r[5] != null && r[5] < q.bath) continue
      if (q.car && !(r[6] >= 1)) continue
      if (q.suburbs.length && !q.suburbs.includes(r[2])) continue
      const sub = subs[r[2]]
      if (q.prefs.includes('safety') && strictSafety) {
        const s = sub?.scores?.safety
        if (s == null || scoreRank.safety(s) < 0.5) continue // safer half of City of Sydney suburbs
      }
      out.push(i)
    }
    return out
  }

  const score = (i) => {
    const r = addresses[i], sub = subs[r[2]]
    let s = 0
    for (const key of q.prefs) {
      if (key === 'station') s += r[18] != null ? Math.max(0, 1 - r[18] / 1200) : 0
      else if (key === 'water') s += r[19] != null ? Math.max(0, 1 - r[19] / 800) : 0
      else if (key === 'safety') {
        s += (scoreRank.safety(sub?.scores?.safety) ?? 0) * 0.6
        const c = lifestyle.mb_crime[r[17]]
        s += c != null ? (1 - crimeRank(c)) * 0.6 : 0
      } else s += scoreRank[key](sub?.scores?.[key]) ?? 0
    }
    if (budget) s += 0.5 * Math.min(1, r[3] / budget) // more home for the money, within budget
    return s
  }

  const rank = (ids) => {
    const scored = ids.map((i) => [i, score(i)]).sort((a, b) => b[1] - a[1])
    // At most 2 flats per building, and at most 8 per suburb unless the user named suburbs
    const perBuilding = new Map(), perSuburb = new Map(), picked = []
    const suburbCap = q.suburbs.length ? Infinity : 8
    for (const [i] of scored) {
      const bk = addresses[i][7], n = perBuilding.get(bk) || 0
      const sk = addresses[i][2], ns = perSuburb.get(sk) || 0
      if (n >= 2 || ns >= suburbCap) continue
      perBuilding.set(bk, n + 1)
      perSuburb.set(sk, ns + 1)
      picked.push(i)
      if (picked.length >= limit) break
    }
    return picked
  }

  let pool = base(true)
  let relaxedSafety = false
  if (q.prefs.includes('safety') && budget && !pool.some((i) => addresses[i][3] <= budget)) {
    const loose = base(false)
    if (loose.some((i) => addresses[i][3] <= budget)) { pool = loose; relaxedSafety = true }
  }
  const within = budget ? pool.filter((i) => addresses[i][3] <= budget) : pool
  const results = rank(within)

  // When few or no flats fit the budget, also show the closest options just above it
  let closest = []
  if (budget && results.length < 5) {
    const above = pool.filter((i) => addresses[i][3] > budget).sort((a, b) => addresses[a][3] - addresses[b][3])
    closest = rank(above.slice(0, 60)).sort((a, b) => addresses[a][3] - addresses[b][3]).slice(0, 10)
  }

  // Suburb summary for the matches
  const bySub = new Map()
  for (const i of within) { const s = addresses[i][2]; if (!bySub.has(s)) bySub.set(s, []); bySub.get(s).push(addresses[i][3]) }
  const suburbCards = [...bySub.entries()]
    .map(([name, vals]) => {
      vals.sort((a, b) => a - b)
      const L = subs[name]
      return { name, count: vals.length, median: vals[Math.floor(vals.length / 2)], safety: L?.scores?.safety,
        income: L?.median_income, rent: L?.rent_unit_week, crimeVerdict: L?.crime_verdict }
    })
    .sort((a, b) => results.filter((i) => addresses[i][2] === b.name).length - results.filter((i) => addresses[i][2] === a.name).length || b.count - a.count)
    .slice(0, 4)

  return { q, budget, incomeBudget, results, closest, suburbCards, matches: within.length, relaxedSafety,
    reply: describe(q, budget, incomeBudget, within.length, results, closest, addresses, relaxedSafety) }
}

function describe(q, budget, incomeBudget, n, results, closest, addresses, relaxedSafety) {
  const parts = []
  const kind = q.bed != null ? (q.bed === 0 ? 'studio' : `${q.bed}-bedroom`) : ''
  const what = (n2) => `${kind} flat${n2 === 1 ? '' : 's'}${q.car ? ' with parking' : ''}`.trim()
  if (q.income) {
    parts.push(`On a ${moneyShort(q.income)} income, a common lending rule of thumb puts a purchase price around ${moneyShort(incomeBudget)} (about 5× income borrowed plus a 20% deposit).`)
    if (q.budget && q.budget > incomeBudget) parts.push(`Your ${moneyShort(q.budget)} budget is above that, so check your borrowing capacity with a lender.`)
    else if (q.budget) parts.push(`Your ${moneyShort(q.budget)} budget sits within that range.`)
  }
  const prefText = q.prefs.length ? ` ranked for ${q.prefs.map((k) => PREFS.find((p) => p.key === k).label).join(', ')}` : ''
  const where = q.suburbs.length ? ` in ${q.suburbs.join(', ')}` : ''
  if (results.length) {
    parts.push(`I found ${n.toLocaleString('en-AU')} ${what(n)}${where} valued${budget ? ` at or under ${moneyShort(budget)}` : ''}. ${results.length > 1 ? `Showing the top ${results.length}${prefText}` : 'It is shown'} on the map.`)
    if (closest.length) parts.push(`That's very few, so I've also marked ${closest.length} more just above budget, from ${moneyShort(addresses[closest[0]][3])}.`)
    if (relaxedSafety) parts.push('None were in the safer half of suburbs, so I widened the search and ranked by street-level crime instead.')
  } else if (closest.length) {
    parts.push(`No ${what(2)}${where} are valued under ${moneyShort(budget)}${q.prefs.includes('safety') ? ' in the safer suburbs' : ''}. The most affordable start at ${moneyShort(addresses[closest[0]][3])}. I've shown the 10 closest on the map.`)
  } else {
    parts.push(`I couldn't find ${what(2)}${where} matching that. Try a different bedroom count or suburb.`)
  }
  if (q.bed != null) parts.push('Only flats with a known bedroom count are included, about a quarter of all addresses.')
  return parts
}
