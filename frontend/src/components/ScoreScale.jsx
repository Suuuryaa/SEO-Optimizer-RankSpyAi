import { BANDS as SCORE_BANDS } from '../lib/score'

const COPY = {
  low: { emoji: '🔴', desc: 'Search engines are missing key information about this page. Start with the fixes marked "Fix first".', width: '40%' },
  mid: { emoji: '🟡', desc: 'A good base. Work through the to-do list to compete for your keyword.', width: '30%' },
  high: { emoji: '🟢', desc: 'Strong on-page basics. Gains now come from content depth and links.', width: '30%' },
}

const BANDS = SCORE_BANDS.map(b => ({ ...b, ...COPY[b.key], range: `${b.min} – ${b.max}` }))

export default function ScoreScale() {
  return (
    <div style={{ padding: '48px 0' }}>
      <div style={{ maxWidth: '1088px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '48px' }}>
          <h2
            style={{
              fontSize: '28px',
              fontWeight: 800,
              color: '#fff',
              letterSpacing: '-0.5px',
            }}
          >
            Understanding Your SEO Score
          </h2>
        </div>

        {/* Composite bar */}
        <div
          style={{
            display: 'flex',
            borderRadius: '10px',
            overflow: 'hidden',
            height: '10px',
            marginBottom: '40px',
            gap: '3px',
          }}
        >
          {BANDS.map((b) => (
            <div
              key={b.label}
              style={{
                height: '100%',
                width: b.width,
                background: b.color,
                borderRadius: '3px',
              }}
            />
          ))}
        </div>

        {/* Band cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '16px',
          }}
        >
          {BANDS.map((b) => (
            <div
              key={b.label}
              style={{
                background: b.bg,
                border: `1px solid ${b.border}`,
                borderRadius: '12px',
                padding: '24px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '22px' }} aria-hidden="true">{b.emoji}</span>
                <div>
                  <h3 style={{ fontSize: '13px', fontWeight: 700, color: b.color, margin: 0 }}>{b.label}</h3>
                  <div style={{ fontSize: '12px', color: '#a0a0a0', marginTop: '1px' }}>{b.range}</div>
                </div>
              </div>
              <div style={{ fontSize: '13px', color: '#a0a0a0', lineHeight: '1.6' }}>{b.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
