import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const STEPS = [
  {
    number: '01',
    title: 'Enter Your URL',
    desc: 'Paste any webpage URL and your target keyword into the analyzer.',
  },
  {
    number: '02',
    title: 'We Crawl & Analyze',
    desc: 'RankSpy AI fetches your page like a search engine bot and runs 200+ checks instantly.',
  },
  {
    number: '03',
    title: 'Get Actionable Insights',
    desc: 'Receive a scored report with prioritized fixes, competitor data, and AI recommendations.',
  },
]

export default function HowItWorks() {
  const sectionRef = useRef(null)
  const headingRef = useRef(null)
  const stepsRef = useRef([])
  const lineRef = useRef(null)

  useEffect(() => {
    const heading = headingRef.current
    const steps = stepsRef.current.filter(Boolean)
    const line = lineRef.current

    gsap.set(heading, { opacity: 0, y: 30 })
    steps.forEach((s) => gsap.set(s, { opacity: 0, y: 40 }))
    gsap.set(line, { scaleX: 0, transformOrigin: 'left center' })

    ScrollTrigger.create({
      trigger: sectionRef.current,
      start: 'top 75%',
      onEnter: () => {
        gsap.to(heading, { opacity: 1, y: 0, duration: 0.8, ease: 'power3.out' })
        gsap.to(line, { scaleX: 1, duration: 1.2, ease: 'power2.inOut', delay: 0.3 })
        steps.forEach((s, i) =>
          gsap.to(s, { opacity: 1, y: 0, duration: 0.7, ease: 'power3.out', delay: 0.2 + i * 0.15 })
        )
      },
    })

    const t = setTimeout(() => ScrollTrigger.refresh(), 300)
    return () => {
      clearTimeout(t)
      ScrollTrigger.getAll().forEach((st) => st.kill())
    }
  }, [])

  return (
    <div ref={sectionRef} style={{ padding: '100px 24px' }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        <div ref={headingRef} style={{ textAlign: 'center', marginBottom: '72px' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#e63946', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '16px' }}>
            The process
          </div>
          <h2 style={{ fontSize: 'clamp(28px, 5vw, 44px)', fontWeight: 800, color: '#fff', letterSpacing: '-1.5px' }}>
            How It Works
          </h2>
        </div>

        <div style={{ position: 'relative' }}>
          {/* Animated connector line */}
          <div style={{ position: 'absolute', top: '28px', left: '16.6%', right: '16.6%', height: '1px', overflow: 'hidden' }}>
            <div
              ref={lineRef}
              style={{ height: '100%', background: 'linear-gradient(90deg, #e63946, rgba(230,57,70,0.3))' }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'center' }}>
            {STEPS.map((step, i) => (
              <div
                key={step.number}
                ref={(el) => (stepsRef.current[i] = el)}
                style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '0 24px' }}
              >
                <div
                  style={{
                    width: '56px',
                    height: '56px',
                    borderRadius: '50%',
                    background: '#0d0d0d',
                    border: '1px solid #2a2a2a',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '28px',
                    position: 'relative',
                    zIndex: 1,
                    flexShrink: 0,
                  }}
                >
                  <span style={{ fontSize: '13px', fontWeight: 800, color: '#e63946', letterSpacing: '0.05em' }}>
                    {step.number}
                  </span>
                </div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: '#fff', marginBottom: '12px', letterSpacing: '-0.3px' }}>
                  {step.title}
                </div>
                <div style={{ fontSize: '13px', color: '#505050', lineHeight: '1.65', maxWidth: '220px' }}>
                  {step.desc}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
