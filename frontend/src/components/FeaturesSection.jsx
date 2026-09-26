import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

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
    desc: 'Evaluates word count, keyword density, duplicate content, heading structure, and readability scores.',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
      </svg>
    ),
    title: 'Link Structure',
    desc: 'Maps internal and external links, anchor text quality, broken links, and crawl depth.',
  },
  {
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="13,2 3,14 12,14 11,22 21,10 12,10 13,2"/>
      </svg>
    ),
    title: 'Page Speed',
    desc: 'Google PageSpeed scores, Core Web Vitals, render-blocking resources, and load time breakdown.',
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
  const sectionRef = useRef(null)
  const headingRef = useRef(null)
  const cardsRef = useRef([])

  useEffect(() => {
    const heading = headingRef.current
    const cards = cardsRef.current.filter(Boolean)

    gsap.set(heading, { opacity: 0, y: 40 })
    cards.forEach((card) => gsap.set(card, { opacity: 0, y: 50 }))

    ScrollTrigger.create({
      trigger: heading,
      start: 'top 85%',
      onEnter: () => gsap.to(heading, { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out' }),
    })

    cards.forEach((card, i) => {
      ScrollTrigger.create({
        trigger: card,
        start: 'top 90%',
        onEnter: () =>
          gsap.to(card, {
            opacity: 1,
            y: 0,
            duration: 0.65,
            ease: 'power3.out',
            delay: (i % 3) * 0.1,
          }),
      })
    })

    // Refresh after fonts/images settle
    const t = setTimeout(() => ScrollTrigger.refresh(), 300)
    return () => {
      clearTimeout(t)
      ScrollTrigger.getAll().forEach((st) => st.kill())
    }
  }, [])

  return (
    <div ref={sectionRef} style={{ padding: '100px 24px' }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        <div ref={headingRef} style={{ textAlign: 'center', marginBottom: '64px' }}>
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
            <span style={{ color: '#444' }}>Needs to Rank</span>
          </h2>
          <p style={{ fontSize: '15px', color: '#505050' }}>200+ SEO factors analyzed in seconds.</p>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '1px',
            background: '#1a1a1a',
            borderRadius: '16px',
            overflow: 'hidden',
          }}
        >
          {FEATURES.map((f, i) => (
            <div
              key={f.title}
              ref={(el) => (cardsRef.current[i] = el)}
              style={{ background: '#0d0d0d', padding: '32px 28px', display: 'flex', flexDirection: 'column', gap: '14px', cursor: 'default', transition: 'background 0.25s' }}
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
              <div style={{ fontSize: '14px', fontWeight: 700, color: '#e0e0e0', letterSpacing: '-0.3px' }}>{f.title}</div>
              <div style={{ fontSize: '13px', color: '#505050', lineHeight: '1.65' }}>{f.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
