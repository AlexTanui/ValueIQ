export const money = (v) => (v == null ? '–' : '$' + Math.round(v).toLocaleString('en-AU'))

export const moneyShort = (v) => {
  if (v == null) return '–'
  if (v >= 1e6) return '$' + (v / 1e6).toFixed(v >= 1e7 ? 1 : 2) + 'M'
  return '$' + Math.round(v / 1e3) + 'k'
}

export const pct = (v, digits = 1) => (v * 100).toFixed(digits) + '%'

// Address rows from addresses.json, as named fields.
export const addressRow = (r) => ({
  id: r[0], address: r[1], suburb: r[2], value: r[3], bed: r[4], bath: r[5], car: r[6],
  building: r[7], lat: r[8], lng: r[9], own: r[10], ownYears: r[11], bldbed: r[12], bldbedN: r[13],
  nbr: r[14], floor: r[15], commercial: !!r[16],
})

export const buildingRow = (r, i) => ({
  i, street: r[0], suburb: r[1], lat: r[2], lng: r[3], value: r[4], units: r[5],
  floors: r[6], sales: r[7], commercial: r[8],
})
