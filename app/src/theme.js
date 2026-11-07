// Colour tokens for map layers (MapLibre paint can't read CSS variables).
// Values from the dataviz reference palette; light and dark stepped separately.

export const BASEMAP = {
  light: 'https://tiles.openfreemap.org/styles/positron',
  dark: 'https://tiles.openfreemap.org/styles/dark',
}

export const PALETTE = {
  light: {
    // Sequential blue, low -> high value (7 steps, starting at step 250 so the lightest still reads on the basemap)
    seq: ['#b7d3f6', '#86b6ef', '#5598e7', '#2a78d6', '#1c5cab', '#104281', '#0d366b'],
    ring: '#ffffff',
    // Diverging: under-valued (blue) <- within 10% (grey) -> over-valued (red)
    div: { under2: '#1c5cab', under1: '#86b6ef', within: '#a9a8a1', over1: '#f0a3a2', over2: '#c42e2e' },
    selected: '#eb6834',
  },
  dark: {
    seq: ['#184f95', '#1c5cab', '#256abf', '#3987e5', '#6da7ec', '#9ec5f4', '#cde2fb'],
    ring: '#1a1a19',
    div: { under2: '#86b6ef', under1: '#2a78d6', within: '#6b6a65', over1: '#c44a4a', over2: '#ff8f8e' },
    selected: '#ff8a5c',
  },
}

export const ERROR_BINS = [
  { key: 'under2', label: 'Under by more than 20%', test: (e) => e < -20 },
  { key: 'under1', label: 'Under by 10–20%', test: (e) => e >= -20 && e < -10 },
  { key: 'within', label: 'Within 10%', test: (e) => e >= -10 && e <= 10 },
  { key: 'over1', label: 'Over by 10–20%', test: (e) => e > 10 && e <= 20 },
  { key: 'over2', label: 'Over by more than 20%', test: (e) => e > 20 },
]

export function prefersDark() {
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
}
