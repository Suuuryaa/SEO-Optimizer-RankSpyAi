import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const TICKER_ITEMS = [
  'Core Web Vitals', 'Keyword Density', 'SERP Position Tracking',
  'Meta Tag Optimization', 'Schema Markup', 'Page Speed Insights',
  'Competitor Gap Analysis', 'E-E-A-T Signals', 'Content Freshness',
  'Structured Data', 'Open Graph Tags', 'Domain Authority',
]
const doubled = [...TICKER_ITEMS, ...TICKER_ITEMS]

export default function Hero() {
  const heroRef = useRef(null)
  const titleRef = useRef(null)
  const subRef = useRef(null)
  const glowRef = useRef(null)
  const pillsRef = useRef(null)

  useEffect(() => {
    const el = {
      title: titleRef.current,
      sub: subRef.current,
      pills: pillsRef.current,
    }

    // Set initial hidden state immediately (no flash)
    gsap.set(el.title, { opacity: 0, y: 50 })
    gsap.set(el.sub, { opacity: 0, y: 30 })
    gsap.set(el.pills, { opacity: 0, y: 20 })

    // Entrance timeline — runs once on load
    const tl = gsap.timeline({ delay: 0.1 })
    tl.to(el.title, { opacity: 1, y: 0, duration: 0.9, ease: 'power3.out' })
      .to(el.sub,   { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out' }, '-=0.5')
      .to(el.pills, { opacity: 1, y: 0, duration: 0.7, ease: 'power3.out' }, '-=0.4')

    // Scroll fade-out — only registers after entrance finishes
    tl.call(() => {
      gsap.to(el.title, {
        scrollTrigger: {
          trigger: heroRef.current,
          start: 'top top',
          end: '+=350',
          scrub: 1.2,
        },
        y: -70,
        opacity: 0,
        scale: 0.93,
        ease: 'none',
      })

      gsap.to(el.sub, {
        scrollTrigger: {
          trigger: heroRef.current,
          start: 'top top',
          end: '+=250',
          scrub: 1,
        },
        y: -40,
        opacity: 0,
        ease: 'none',
      })

      ScrollTrigger.refresh()
    })

    // Mouse parallax glow
    const onMouseMove = (e) => {
      if (!glowRef.current) return
      const x = (e.clientX / window.innerWidth - 0.5) * 60
      const y = (e.clientY / window.innerHeight - 0.5) * 40
      gsap.to(glowRef.current, { x, y, duration: 1.4, ease: 'power2.out' })
    }
    window.addEventListener('mousemove', onMouseMove)

    return () => {
      tl.kill()
      ScrollTrigger.getAll().forEach((t) => t.kill())
      window.removeEventListener('mousemove', onMouseMove)
    }
  }, [])

  return (
    <div ref={heroRef} style={{ position: 'relative', overflow: 'hidden', borderBottom: '1px solid #1a1a1a' }}>
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
        <div ref={titleRef} style={{ willChange: 'transform, opacity' }}>
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
        <div ref={subRef} style={{ willChange: 'transform, opacity' }}>
          <p
            style={{
              fontSize: 'clamp(16px, 2.5vw, 20px)',
              color: '#666',
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
          ref={pillsRef}
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: '8px',
            maxWidth: '640px',
            margin: '0 auto',
            willChange: 'transform, opacity',
          }}
        >
          {[
            'Real-Time Intelligence', 'Competitive Benchmarking',
            'Technical SEO Audit', 'AI-Powered Insights',
            'Enterprise-Grade Analysis', 'Strategic Action Plans',
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
              <span style={{ color: '#505050', fontSize: '11px', fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
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
