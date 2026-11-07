// First screen: say what the tool does and put the scan form right there.
// (Replaces the giant wordmark, buzzword pills and ticker, which pushed the
// form below the fold on most screens.)
export default function Hero({ children }) {
  return (
    <div className="no-print hero" style={{ position: 'relative', overflow: 'hidden', borderBottom: '1px solid #1a1a1a' }}>
      <div
        aria-hidden="true"
        style={{
          position: 'absolute', top: '-10%', left: '50%', transform: 'translateX(-50%)',
          width: '900px', height: '420px', pointerEvents: 'none', zIndex: 0,
          background: 'radial-gradient(ellipse at center, rgba(230,57,70,0.12) 0%, transparent 70%)',
        }}
      />

      <div style={{ position: 'relative', zIndex: 1, maxWidth: '960px', margin: '0 auto', padding: '28px 16px 32px' }}>
        <div style={{ textAlign: 'center', marginBottom: '20px' }} className="hero-in">
          <div
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '8px',
              background: 'rgba(230,57,70,0.08)', border: '1px solid rgba(230,57,70,0.22)',
              borderRadius: '100px', padding: '5px 14px', marginBottom: '14px',
              fontSize: '12px', fontWeight: 600, color: '#ff8a93', letterSpacing: '0.02em',
            }}
          >
            Free SEO checker · AI-visibility · Competitor comparison
          </div>

          <h1
            style={{
              fontSize: 'clamp(30px, 4.6vw, 52px)', fontWeight: 800, letterSpacing: '-0.03em',
              lineHeight: 1.08, color: '#fff', margin: '0 auto 12px', maxWidth: '820px',
            }}
          >
            Find out why your page isn&rsquo;t ranking <span style={{ color: '#e63946' }}>and exactly what to fix</span>
          </h1>

          <p style={{ fontSize: 'clamp(15px, 1.6vw, 18px)', color: 'var(--text-body, #a0a0a0)', lineHeight: 1.55, maxWidth: '700px', margin: '0 auto' }}>
            Paste a page and your keyword. Get a plain-English to-do list, an AI-visibility score
            and a side-by-side with the sites beating you on Google.
          </p>
        </div>

        <div className="hero-in" style={{ animationDelay: '0.1s', maxWidth: '760px', margin: '0 auto' }}>
          {children}
        </div>

        <ul
          className="hero-trust"
          style={{
            listStyle: 'none', padding: 0, margin: '14px auto 0', display: 'flex', flexWrap: 'wrap',
            justifyContent: 'center', gap: '8px 22px', fontSize: '13px', color: 'var(--text-muted, #8a8a8a)',
          }}
        >
          {['Free · no sign-up', '~1 minute per scan', '30+ on-page checks', 'Real Google positions'].map((t) => (
            <li key={t} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
              <span aria-hidden="true" style={{ color: '#22c55e' }}>✓</span>{t}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
