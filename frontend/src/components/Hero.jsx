import { useEffect, useRef } from 'react'

const TICKER_ITEMS = [
  'Keyword Density', 'SERP Position Tracking',
  'Meta Tag Optimization', 'Schema Markup',
  'Competitor Gap Analysis', 'E-E-A-T Signals', 'Content Freshness',
  'Structured Data', 'Open Graph Tags', 'AI Crawler Access',
]
const doubled = [...TICKER_ITEMS, ...TICKER_ITEMS]

export default function Hero() {
  const glowRef = useRef(null)

  // Ambient glow drifts with the mouse (skipped for reduced motion)
  useEffect(() => {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    let frame = 0
    const onMouseMove = (e) => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(() => {
        if (!glowRef.current) return
        const x = (e.clientX / window.innerWidth - 0.5) * 60
        const y = (e.clientY / window.innerHeight - 0.5) * 40
        glowRef.current.style.transform = `translate(calc(-50% + ${x}px), ${y}px)`
      })
    }
    window.addEventListener('mousemove', onMouseMove, { passive: true })
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('mousemove', onMouseMove)
    }
  }, [])

  return (
    <div className="no-print" style={{ position: 'relative', overflow: 'hidden', borderBottom: '1px solid #1a1a1a' }}>
      {/* Ambient glow follows mouse */}
      <div
        ref={glowRef}
        style={{
          position: 'absolute',
          top: '10%',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '700px',
          height: '400px',
          background: 'radial-gradient(ellipse at center, rgba(230,57,70,0.13) 0%, transparent 70%)',
          pointerEvents: 'none',
          zIndex: 0,
          willChange: 'transform',
          transition: 'transform 1.4s cubic-bezier(0.22, 1, 0.36, 1)',
        }}
      />

      <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', padding: '96px 24px 72px' }}>
        {/* Live badge */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'rgba(230,57,70,0.08)',
            border: '1px solid rgba(230,57,70,0.2)',
            borderRadius: '100px',
            padding: '5px 14px',
            marginBottom: '36px',
          }}
        >
          <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#e63946', animation: 'pulse 2s ease infinite' }} />
          <span style={{ fontSize: '11px', fontWeight: 700, color: '#e63946', letterSpacing: '0.1em' }}>
            AI-POWERED SEO INTELLIGENCE
          </span>
        </div>

        {/* Big title */}
        <div className="hero-in">
          <h1
            style={{
              fontSize: 'clamp(56px, 10vw, 100px)',
              fontWeight: 900,
              letterSpacing: '-4px',
              lineHeight: 0.95,
              color: '#fff',
              marginBottom: '8px',
            }}
          >
            RANK
            <span style={{ color: '#e63946', position: 'relative', display: 'inline-block', marginLeft: '10px' }}>
              SPY
              <span
                style={{
                  position: 'absolute',
                  bottom: '-2px',
                  left: 0,
                  right: 0,
                  height: '3px',
                  background: 'linear-gradient(90deg, transparent, #e63946, transparent)',
                  borderRadius: '2px',
                }}
              />
            </span>
          </h1>
          <div
            style={{
              fontSize: 'clamp(56px, 10vw, 100px)',
              fontWeight: 900,
              letterSpacing: '-4px',
              lineHeight: 0.95,
              background: 'linear-gradient(135deg, #fff 30%, #3a3a3a 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              marginBottom: '40px',
            }}
          >
            AI
          </div>
        </div>

        {/* Subtitle */}
        <div className="hero-in" style={{ animationDelay: '0.15s' }}>
          <p
            style={{
              fontSize: 'clamp(16px, 2.5vw, 20px)',
              color: '#a0a0a0',
              letterSpacing: '-0.01em',
              lineHeight: 1.5,
              maxWidth: '520px',
              margin: '0 auto 48px',
            }}
          >
            SEO Audit & Competitor Intel.{' '}
            <span style={{ color: '#e63946' }}>Powered by AI</span>, driven by data.
          </p>
        </div>

        {/* Pills */}
        <div
          className="hero-in"
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: '8px',
            maxWidth: '640px',
            margin: '0 auto',
            animationDelay: '0.3s',
          }}
        >
          {[
            'Plain-English to-do list', 'Competitive Benchmarking',
            'Technical SEO Audit', 'AI-Powered Insights',
            'Real Google positions', 'Strategic Action Plans',
          ].map((p) => (
            <span key={p} className="feature-pill">{p}</span>
          ))}
        </div>
      </div>

      {/* Ticker */}
      <div
        className="ticker-wrap"
        style={{
          overflow: 'hidden',
          borderTop: '1px solid #1a1a1a',
          background: '#080808',
          padding: '12px 0',
          userSelect: 'none',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(90deg, #080808 0%, transparent 8%, transparent 92%, #080808 100%)',
            zIndex: 2,
            pointerEvents: 'none',
          }}
        />
        <div className="ticker-track">
          {doubled.map((item, i) => (
            <span key={i} style={{ display: 'inline-flex', alignItems: 'center', whiteSpace: 'nowrap' }}>
              <span style={{ color: '#8a8a8a', fontSize: '11px', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                {item}
              </span>
              <span style={{ color: 'rgba(230,57,70,0.5)', margin: '0 20px', fontSize: '8px' }}>◆</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
