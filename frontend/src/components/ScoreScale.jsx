const BANDS = [
  {
    emoji: '🔴',
    range: '0 – 39',
    label: 'Critical Issues',
    color: '#e63946',
    bg: 'rgba(230,57,70,0.08)',
    border: 'rgba(230,57,70,0.25)',
    desc: 'Serious problems blocking your rankings. Immediate action required.',
    width: '40%',
  },
  {
    emoji: '🟡',
    range: '40 – 69',
    label: 'Needs Work',
    color: '#f97316',
    bg: 'rgba(249,115,22,0.08)',
    border: 'rgba(249,115,22,0.25)',
    desc: 'Optimization opportunities exist. Work through the priority list.',
    width: '30%',
  },
  {
    emoji: '🟢',
    range: '70 – 100',
    label: 'Strong Foundation',
    color: '#22c55e',
    bg: 'rgba(34,197,94,0.08)',
    border: 'rgba(34,197,94,0.25)',
    desc: 'Great SEO health. Focus on content and authority building.',
    width: '30%',
  },
]

export default function ScoreScale() {
  return (
    <div style={{ padding: '80px 24px' }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
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
            gridTemplateColumns: 'repeat(3, 1fr)',
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
                <span style={{ fontSize: '22px' }}>{b.emoji}</span>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: b.color }}>{b.label}</div>
                  <div style={{ fontSize: '12px', color: '#606060', marginTop: '1px' }}>{b.range}</div>
                </div>
              </div>
              <div style={{ fontSize: '13px', color: '#808080', lineHeight: '1.6' }}>{b.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
