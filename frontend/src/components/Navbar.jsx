import { useState, useEffect } from 'react'

const NAV_LINKS = [
  { label: 'Features',     href: '#features' },
  { label: 'How it Works', href: '#how-it-works' },
  { label: 'FAQ',          href: '#faq' },
  { label: 'Score Guide',  href: '#score-guide' },
]

const linkStyle = {
  fontSize: '13px',
  color: '#b0b0b0',
  padding: '6px 12px',
  borderRadius: '6px',
  textDecoration: 'none',
  transition: 'color 0.15s',
}

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 50)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    if (!menuOpen) return
    function onKey(e) { if (e.key === 'Escape') setMenuOpen(false) }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [menuOpen])

  return (
    <nav
      aria-label="Main"
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
        gap: '12px',
        padding: '0 16px',
        background: scrolled || menuOpen ? 'rgba(8,8,8,0.92)' : '#080808',
        borderBottom: '1px solid #1a1a1a',
        backdropFilter: scrolled ? 'blur(12px)' : 'none',
        WebkitBackdropFilter: scrolled ? 'blur(12px)' : 'none',
        transition: 'background 0.2s, backdrop-filter 0.2s',
      }}
    >
      {/* Logo */}
      <a href="#top" aria-label="RankSpy AI home" style={{ textDecoration: 'none' }} onClick={() => setMenuOpen(false)}>
        <span style={{ fontSize: '16px', fontWeight: 800, color: '#fff', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>
          RANKSPY <span style={{ color: '#e63946' }}>AI</span>
        </span>
      </a>

      {/* Center nav links (desktop) */}
      <div
        className="navbar-center"
        style={{ display: 'flex', gap: '4px', position: 'absolute', left: '50%', transform: 'translateX(-50%)' }}
      >
        {NAV_LINKS.map(link => (
          <a key={link.href} href={link.href} className="nav-link" style={linkStyle}>{link.label}</a>
        ))}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {/* CTA */}
        <a
          href="#scan"
          className="navbar-cta"
          style={{
            background: '#e63946',
            fontSize: '13px',
            fontWeight: 600,
            color: '#fff',
            padding: '8px 18px',
            borderRadius: '8px',
            letterSpacing: '0.02em',
            textDecoration: 'none',
            whiteSpace: 'nowrap',
          }}
          onClick={() => {
            setMenuOpen(false)
            setTimeout(() => document.getElementById('url-input')?.focus({ preventScroll: true }), 300)
          }}
        >
          Analyze Now
        </a>

        {/* Menu button (mobile) */}
        <button
          type="button"
          className="navbar-menu-btn"
          aria-expanded={menuOpen}
          aria-controls="mobile-menu"
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          onClick={() => setMenuOpen(o => !o)}
          style={{
            background: 'none', border: '1px solid #2a2a2a', borderRadius: '8px', color: '#fff',
            width: '40px', height: '40px', cursor: 'pointer', fontSize: '18px', lineHeight: 1,
            alignItems: 'center', justifyContent: 'center',
          }}
        >
          {menuOpen ? '✕' : '☰'}
        </button>
      </div>

      {menuOpen && (
        <div
          id="mobile-menu"
          className="mobile-menu"
          style={{
            position: 'absolute', top: '60px', left: 0, right: 0,
            background: '#0b0b0b', borderBottom: '1px solid #1a1a1a',
            padding: '8px 16px 16px', display: 'flex', flexDirection: 'column', gap: '2px',
          }}
        >
          {[...NAV_LINKS, { label: 'Analyze a page', href: '#scan' }].map(link => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setMenuOpen(false)}
              style={{ ...linkStyle, fontSize: '15px', padding: '12px 8px', color: '#e0e0e0' }}
            >
              {link.label}
            </a>
          ))}
        </div>
      )}

      <style>{`
        .nav-link:hover { color: #fff !important; }
        .navbar-menu-btn { display: none; }
        @media (max-width: 767px) {
          .navbar-center { display: none !important; }
          .navbar-menu-btn { display: inline-flex; }
        }
        @media (min-width: 768px) {
          .mobile-menu { display: none !important; }
        }
      `}</style>
    </nav>
  )
}
