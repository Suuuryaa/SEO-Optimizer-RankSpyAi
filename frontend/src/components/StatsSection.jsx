import { useReveal } from '../lib/useReveal'

const STATS = [
  { value: '30+', label: 'On-page checks' },
  { value: '~1 min', label: 'Typical scan' },
  { value: 'Up to 8', label: 'Competitors compared' },
  { value: 'Free', label: 'No sign-up' },
]

export default function StatsSection() {
  const sectionRef = useReveal()

  return (
    <div ref={sectionRef} style={{ padding: '64px 0' }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1px', background: '#161616', borderRadius: '14px', overflow: 'hidden' }}>
          {STATS.map((s, i) => (
            <div
              key={s.label}
              className="reveal"
              style={{ background: '#0a0a0a', padding: '36px 20px', textAlign: 'center', transitionDelay: `${i * 0.1}s` }}
            >
              <div style={{ fontSize: 'clamp(28px, 4vw, 40px)', fontWeight: 900, color: '#fff', letterSpacing: '-2px', marginBottom: '8px', lineHeight: 1 }}>
                {s.value}
              </div>
              <div style={{ fontSize: '12px', color: '#8a8a8a', letterSpacing: '0.06em', fontWeight: 600, textTransform: 'uppercase' }}>
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
