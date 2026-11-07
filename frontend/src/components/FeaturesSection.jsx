import { useReveal } from '../lib/useReveal'

const FEATURES = [
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
      </svg>
    ),
    title: 'Meta & Title Tags',
    desc: 'Analyzes title length, meta descriptions, canonical tags, and keyword placement across your page.',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
      </svg>
    ),
    title: 'Content Quality',
    desc: 'Evaluates word count, keyword use and density, heading structure, and readability.',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
      </svg>
    ),
    title: 'Link Structure',
    desc: 'Counts internal and external links and checks your heading structure.',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="13,2 3,14 12,14 11,22 21,10 12,10 13,2"/>
      </svg>
    ),
    title: 'Competitor Comparison',
    desc: 'Finds up to 8 competitors for your keyword, scores their pages and looks up real Google positions.',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>
      </svg>
    ),
    title: 'AI & GEO Signals',
    desc: 'Checks AI crawler access, LLMs.txt, E-E-A-T signals, and citability for AI-powered search.',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </svg>
    ),
    title: 'Technical SEO',
    desc: 'HTTPS, mobile viewport, robots meta, Open Graph tags, schema markup, and server config.',
  },
]

export default function FeaturesSection() {
  const sectionRef = useReveal()

  return (
    <div ref={sectionRef} style={{ padding: '56px 0' }}>
      <div style={{ maxWidth: '1088px', margin: '0 auto' }}>
        <div className="reveal" style={{ textAlign: 'center', marginBottom: '48px' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#e63946', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '16px' }}>
            What we analyze
          </div>
          <h2
            style={{
              fontSize: 'clamp(28px, 5vw, 44px)',
              fontWeight: 800,
              color: '#fff',
              letterSpacing: '-1.5px',
              lineHeight: 1.1,
              marginBottom: '16px',
            }}
          >
            Everything Your Site
            <br />
            <span style={{ color: '#8a8a8a' }}>Needs to Rank</span>
          </h2>
          <p style={{ fontSize: '15px', color: '#a0a0a0' }}>30+ on-page checks in a typical one-minute scan.</p>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))',
            gap: '1px',
            background: '#1a1a1a',
            borderRadius: '16px',
            overflow: 'hidden',
          }}
        >
          {FEATURES.map((f, i) => (
            <div
              key={f.title}
              className="reveal"
              style={{ background: '#0d0d0d', padding: '28px 24px', display: 'flex', flexDirection: 'column', gap: '14px', cursor: 'default', transitionDelay: `${(i % 3) * 0.1}s` }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#131313'
                const icon = e.currentTarget.querySelector('.feat-icon')
                if (icon) icon.style.color = '#e63946'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#0d0d0d'
                const icon = e.currentTarget.querySelector('.feat-icon')
                if (icon) icon.style.color = '#3a3a3a'
              }}
            >
              <div
                className="feat-icon"
                style={{
                  color: '#3a3a3a',
                  transition: 'color 0.25s',
                  width: '44px',
                  height: '44px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#161616',
                  borderRadius: '10px',
                  flexShrink: 0,
                }}
              >
                {f.icon}
              </div>
              <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#e0e0e0', letterSpacing: '-0.3px', margin: 0 }}>{f.title}</h3>
              <div style={{ fontSize: '13px', color: '#a0a0a0', lineHeight: '1.65' }}>{f.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
