import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

const STATS = [
  { value: '200+', label: 'SEO Factors Checked' },
  { value: '< 60s', label: 'Analysis Time' },
  { value: '8+', label: 'Competitors Found' },
  { value: 'Free', label: 'No Sign-Up Required' },
]

export default function StatsSection() {
  const sectionRef = useRef(null)
  const itemsRef = useRef([])

  useEffect(() => {
    const items = itemsRef.current.filter(Boolean)
    items.forEach((el) => gsap.set(el, { opacity: 0, y: 30 }))

    ScrollTrigger.create({
      trigger: sectionRef.current,
      start: 'top 82%',
      onEnter: () => {
        items.forEach((el, i) =>
          gsap.to(el, { opacity: 1, y: 0, duration: 0.6, ease: 'power3.out', delay: i * 0.1 })
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
    <div ref={sectionRef} style={{ padding: '80px 24px' }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1px', background: '#161616', borderRadius: '14px', overflow: 'hidden' }}>
          {STATS.map((s, i) => (
            <div
              key={s.label}
              ref={(el) => (itemsRef.current[i] = el)}
              style={{ background: '#0a0a0a', padding: '36px 20px', textAlign: 'center' }}
            >
              <div style={{ fontSize: 'clamp(28px, 4vw, 40px)', fontWeight: 900, color: '#fff', letterSpacing: '-2px', marginBottom: '8px', lineHeight: 1 }}>
                {s.value}
              </div>
              <div style={{ fontSize: '12px', color: '#404040', letterSpacing: '0.06em', fontWeight: 600, textTransform: 'uppercase' }}>
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
