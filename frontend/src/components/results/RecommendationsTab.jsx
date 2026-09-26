const PRIORITY_CONFIG = {
  critical: { emoji: '🔴', label: 'CRITICAL', color: '#e63946', bg: 'rgba(230,57,70,0.1)', border: 'rgba(230,57,70,0.3)' },
  high:     { emoji: '🟠', label: 'HIGH',     color: '#f97316', bg: 'rgba(249,115,22,0.1)', border: 'rgba(249,115,22,0.3)' },
  medium:   { emoji: '🟡', label: 'MEDIUM',   color: '#eab308', bg: 'rgba(234,179,8,0.1)',  border: 'rgba(234,179,8,0.3)'  },
  low:      { emoji: '🟢', label: 'LOW',      color: '#22c55e', bg: 'rgba(34,197,94,0.1)',  border: 'rgba(34,197,94,0.3)'  },
}

function priorityKey(p) {
  const s = (p || '').toLowerCase()
  if (s.includes('critical')) return 'critical'
  if (s.includes('high')) return 'high'
  if (s.includes('medium')) return 'medium'
  return 'low'
}

function RecommendationCard({ rec, index }) {
  const key = priorityKey(rec.priority)
  const cfg = PRIORITY_CONFIG[key]

  return (
    <div
      className="fade-in"
      style={{
        background: '#161616',
        border: `1px solid #2a2a2a`,
        borderLeft: `3px solid ${cfg.color}`,
        borderRadius: '10px',
        padding: '18px',
        animationDelay: `${index * 0.05}s`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
          <span style={{ fontSize: '15px' }}>{cfg.emoji}</span>
          <span style={{ fontSize: '14px', fontWeight: 700, color: '#fff', flex: 1 }}>
            {rec.issue}
          </span>
        </div>
        <span
          style={{
            background: cfg.bg,
            border: `1px solid ${cfg.border}`,
            color: cfg.color,
            fontSize: '9px',
            fontWeight: 800,
            padding: '3px 8px',
            borderRadius: '100px',
            letterSpacing: '0.1em',
            whiteSpace: 'nowrap',
            marginLeft: '12px',
          }}
        >
          {cfg.label}
        </span>
      </div>

      {rec.fix && (
        <div style={{ marginBottom: '8px' }}>
          <span style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase' }}>Fix: </span>
          <span style={{ fontSize: '13px', color: '#a0a0a0' }}>{rec.fix}</span>
        </div>
      )}

      {rec.impact && (
        <div
          style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid #222',
            borderRadius: '6px',
            padding: '8px 12px',
            fontSize: '12px',
            color: '#606060',
          }}
        >
          <span style={{ fontWeight: 700, color: '#888' }}>Impact: </span>{rec.impact}
        </div>
      )}
    </div>
  )
}

export default function RecommendationsTab({ data }) {
  const recs = data.recommendations || []

  const order = ['critical', 'high', 'medium', 'low']
  const sorted = [...recs].sort((a, b) => {
    return order.indexOf(priorityKey(a.priority)) - order.indexOf(priorityKey(b.priority))
  })

  const counts = { critical: 0, high: 0, medium: 0, low: 0 }
  recs.forEach(r => { counts[priorityKey(r.priority)]++ })

  if (recs.length === 0) {
    return (
      <div className="fade-in" style={{ textAlign: 'center', padding: '48px', color: '#606060' }}>
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>✨</div>
        <div style={{ fontSize: '18px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>No Issues Found</div>
        <div style={{ fontSize: '13px' }}>Your page looks great! Keep monitoring for changes.</div>
      </div>
    )
  }

  return (
    <div className="fade-in">
      {/* Summary bar */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
        {Object.entries(counts).map(([k, v]) => {
          const cfg = PRIORITY_CONFIG[k]
          if (v === 0) return null
          return (
            <div
              key={k}
              style={{
                background: cfg.bg,
                border: `1px solid ${cfg.border}`,
                borderRadius: '8px',
                padding: '8px 14px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span style={{ fontSize: '13px' }}>{cfg.emoji}</span>
              <span style={{ fontSize: '13px', fontWeight: 700, color: cfg.color }}>{v}</span>
              <span style={{ fontSize: '11px', color: '#606060' }}>{cfg.label}</span>
            </div>
          )
        })}
        <div style={{ fontSize: '13px', color: '#606060', alignSelf: 'center', marginLeft: 'auto' }}>
          {recs.length} total recommendations
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {sorted.map((rec, i) => (
          <RecommendationCard key={i} rec={rec} index={i} />
        ))}
      </div>
    </div>
  )
}
