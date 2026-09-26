import { useState, useEffect } from 'react'

function scrollToSection(id) {
  if (!id) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
    return
  }
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  else window.scrollTo({ top: 0, behavior: 'smooth' })
}

const NAV_LINKS = [
  { label: 'Features',     id: 'section-features' },
  { label: 'How it Works', id: 'section-how' },
  { label: 'FAQ',          id: 'section-faq' },
  { label: 'Score Guide',  id: 'section-scale' },
]

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [hoveredIdx, setHoveredIdx] = useState(null)

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 50)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <nav
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        height: '60px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 28px',
        background: scrolled ? 'rgba(8,8,8,0.85)' : '#080808',
        borderBottom: '1px solid #1a1a1a',
        backdropFilter: scrolled ? 'blur(12px)' : 'none',
        WebkitBackdropFilter: scrolled ? 'blur(12px)' : 'none',
        transition: 'background 0.2s, backdrop-filter 0.2s',
      }}
    >
      {/* Logo */}
      <button
        onClick={() => scrollToSection(null)}
        style={{
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: 0,
          fontFamily: 'inherit',
        }}
      >
        <span style={{ fontSize: '16px', fontWeight: 800, color: '#fff', letterSpacing: '0.06em' }}>
          RANKSPY <span style={{ color: '#e63946' }}>AI</span>
        </span>
      </button>

      {/* Center nav links — hidden on mobile */}
      <div
        style={{
          display: 'flex',
          gap: '4px',
          position: 'absolute',
          left: '50%',
          transform: 'translateX(-50%)',
        }}
        className="navbar-center"
      >
        {NAV_LINKS.map((link, i) => (
          <button
            key={link.label}
            onClick={() => scrollToSection(link.id)}
            onMouseEnter={() => setHoveredIdx(i)}
            onMouseLeave={() => setHoveredIdx(null)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '13px',
              color: hoveredIdx === i ? '#fff' : '#808080',
              padding: '6px 12px',
              borderRadius: '6px',
              fontFamily: 'inherit',
              transition: 'color 0.15s',
            }}
          >
            {link.label}
          </button>
        ))}
      </div>

      {/* CTA */}
      <button
        onClick={() => scrollToSection(null)}
        style={{
          background: '#e63946',
          border: 'none',
          cursor: 'pointer',
          fontSize: '13px',
          fontWeight: 600,
          color: '#fff',
          padding: '8px 18px',
          borderRadius: '8px',
          fontFamily: 'inherit',
          letterSpacing: '0.02em',
          transition: 'opacity 0.15s',
        }}
        onMouseEnter={e => (e.currentTarget.style.opacity = '0.85')}
        onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
      >
        Analyze Now
      </button>

      <style>{`
        @media (max-width: 768px) {
          .navbar-center { display: none !important; }
        }
      `}</style>
    </nav>
  )
}
