// One shared score band (0–39 / 40–69 / 70–100) used by every score display.
export const BANDS = [
  { key: 'low', min: 0, max: 39, label: 'Critical Issues', color: '#e63946', bg: 'rgba(230,57,70,0.08)', border: 'rgba(230,57,70,0.25)' },
  { key: 'mid', min: 40, max: 69, label: 'Needs Work', color: '#f97316', bg: 'rgba(249,115,22,0.08)', border: 'rgba(249,115,22,0.25)' },
  { key: 'high', min: 70, max: 100, label: 'Strong Foundation', color: '#22c55e', bg: 'rgba(34,197,94,0.08)', border: 'rgba(34,197,94,0.25)' },
]

export function scoreBand(score) {
  const s = Number(score) || 0
  if (s >= 70) return BANDS[2]
  if (s >= 40) return BANDS[1]
  return BANDS[0]
}

export function scoreColor(score) {
  return scoreBand(score).color
}

export function verdictFor(score, keyword) {
  const b = scoreBand(score).key
  if (b === 'low') return 'Search engines are missing key information about this page. Start with the fixes below.'
  if (b === 'mid') {
    return keyword
      ? `Good base. The fixes below should help this page compete for '${keyword}'.`
      : 'Good base. The fixes below should help this page compete.'
  }
  return 'Strong on-page basics. Gains now come from content depth and links.'
}

// Backend priorities carry an emoji ("🔴 CRITICAL"), so match on the letters only
export function prio(p) {
  return String(p ?? '').toUpperCase().replace(/[^A-Z]/g, '')
}

const PRIORITY_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }

export function sortRecs(recs) {
  return [...(recs || [])].sort(
    (a, b) => (PRIORITY_ORDER[prio(a.priority)] ?? 99) - (PRIORITY_ORDER[prio(b.priority)] ?? 99),
  )
}

export function relativeTime(iso) {
  if (!iso) return ''
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return ''
  const mins = Math.max(0, Math.round((Date.now() - t) / 60000))
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hrs = Math.round(mins / 60)
  if (hrs < 24) return `${hrs} h ago`
  return `${Math.round(hrs / 24)} d ago`
}

// Task badges: CRITICAL/HIGH "Fix first", MEDIUM "Fix next", LOW "Nice to have"
export function priorityBadge(raw) {
  const p = prio(raw)
  if (p === 'CRITICAL' || p === 'HIGH') return { bg: 'rgba(230,57,70,0.12)', color: '#ff6b75', border: 'rgba(230,57,70,0.35)', label: 'Fix first' }
  if (p === 'MEDIUM') return { bg: 'rgba(234,179,8,0.12)', color: '#eab308', border: 'rgba(234,179,8,0.35)', label: 'Fix next' }
  return { bg: 'rgba(59,130,246,0.12)', color: '#7aa7ff', border: 'rgba(59,130,246,0.35)', label: 'Nice to have' }
}

// "High - titles are the most important…" → "Titles are the most important…"
export function whyText(impact) {
  const t = String(impact ?? '').replace(/^\s*(critical|high|medium|low)\s*[-–—:]\s*/i, '').trim()
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : ''
}
