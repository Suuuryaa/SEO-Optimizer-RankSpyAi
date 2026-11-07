import { useState, useEffect, useRef } from 'react'

// "/#section" links work from every page (/, /faq)
const NAV_LINKS = [
  { label: 'How it Works', href: '/#how-it-works' },
  { label: 'Score Guide',  href: '/#score-guide' },
  { label: 'FAQ',          href: '/faq' },
]

// What RankSpy actually does today — no features we don't have
const FEATURES = [
  { icon: 'audit',   title: 'On-page SEO audit',     desc: '30+ checks, a score and a plain-English to-do list.', href: '/#scan' },
  { icon: 'rivals',  title: 'Competitor comparison', desc: 'Your main rivals and their real Google positions.',   href: '/#scan' },
  { icon: 'ai',      title: 'AI visibility (GEO)',   desc: 'Can ChatGPT, Perplexity and Claude read your page?',  href: '/#features' },
  { icon: 'browser', title: 'JS rendering & crawl',  desc: 'Reads JavaScript sites the way visitors see them.',   href: '/#scan' },
  { icon: 'pen',     title: 'AI meta tag writer',    desc: 'A better title and description for your keyword.',    href: '/#features' },
  { icon: 'code',    title: 'Schema generator',      desc: 'Ready-to-paste structured data for your page.',       href: '/#features' },
  { icon: 'pin',     title: 'Local SEO check',       desc: 'Phone, address, map and local business signals.',     href: '/#features' },
]

const ICONS = {
  audit:   <><path d="M9 4h6v3H9z" /><path d="M7 5H5v16h14V5h-2" /><path d="m9 13 2 2 4-4" /></>,
  rivals:  <><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></>,
  ai:      <><path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z" /><path d="M19 15l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z" /></>,
  browser: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 9h18" /></>,
  pen:     <><path d="M4 20h4L19 9l-4-4L4 16z" /><path d="m13 7 4 4" /></>,
  code:    <><path d="m8 8-4 4 4 4M16 8l4 4-4 4M14 5l-4 14" /></>,
  pin:     <><path d="M12 21s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z" /><circle cx="12" cy="9" r="2.5" /></>,
  gauge:   <><path d="M4 16a8 8 0 1 1 16 0" /><path d="m12 16 4-5" /></>,
}

function Icon({ name }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ff6b75" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0, marginTop: '1px' }}>
      {ICONS[name]}
    </svg>
  )
}

const linkStyle = {
  fontSize: '13px',
  color: '#b0b0b0',
  padding: '6px 12px',
  borderRadius: '6px',
  textDecoration: 'none',
  transition: 'color 0.15s',
}

function focusScanSoon() {
  setTimeout(() => document.getElementById('url-input')?.focus({ preventScroll: true }), 300)
}

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [featOpen, setFeatOpen] = useState(false)
  const featRef = useRef(null)
  const onHome = typeof window !== 'undefined' && window.location.pathname === '/'

  useEffect(() => {
    function onScroll() { setScrolled(window.scrollY > 50) }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    if (!menuOpen && !featOpen) return
    function onKey(e) { if (e.key === 'Escape') { setMenuOpen(false); setFeatOpen(false) } }
    function onClick(e) { if (featOpen && featRef.current && !featRef.current.contains(e.target)) setFeatOpen(false) }
    document.addEventListener('keydown', onKey)
    document.addEventListener('mousedown', onClick)
    return () => { document.removeEventListener('keydown', onKey); document.removeEventListener('mousedown', onClick) }
  }, [menuOpen, featOpen])

  return (
    <nav
      aria-label="Main"
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100, height: '60px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', padding: '0 16px',
        background: scrolled || menuOpen ? 'rgba(8,8,8,0.92)' : '#080808',
        borderBottom: '1px solid #1a1a1a',
        backdropFilter: scrolled ? 'blur(12px)' : 'none',
        WebkitBackdropFilter: scrolled ? 'blur(12px)' : 'none',
        transition: 'background 0.2s, backdrop-filter 0.2s',
      }}
    >
      {/* Logo */}
      <a href={onHome ? '#top' : '/'} aria-label="RankSpy AI home" style={{ textDecoration: 'none' }} onClick={() => setMenuOpen(false)}>
        <span style={{ fontSize: '16px', fontWeight: 800, color: '#fff', letterSpacing: '0.06em', whiteSpace: 'nowrap' }}>
          RANKSPY <span style={{ color: '#e63946' }}>AI</span>
        </span>
      </a>

      {/* Center nav (desktop) */}
      <div className="navbar-center" style={{ display: 'flex', alignItems: 'center', gap: '4px', position: 'absolute', left: '50%', transform: 'translateX(-50%)' }}>
        <div ref={featRef} style={{ position: 'relative' }}>
          <button
            type="button"
            className="nav-link"
            aria-expanded={featOpen}
            aria-controls="features-menu"
            onClick={() => setFeatOpen(o => !o)}
            style={{ ...linkStyle, background: featOpen ? '#161616' : 'none', border: 'none', cursor: 'pointer', fontFamily: 'inherit', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            Features
            <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true" style={{ transform: featOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}>
              <path d="M1 3l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
            </svg>
          </button>
          {featOpen && (
            <div id="features-menu" className="features-menu">
              {FEATURES.map(f => (
                <a key={f.title} href={f.href} className="features-item" onClick={() => { setFeatOpen(false); if (f.href === '/#scan') focusScanSoon() }}>
                  <Icon name={f.icon} />
                  <span style={{ minWidth: 0 }}>
                    <span style={{ display: 'block', fontSize: '14px', fontWeight: 700, color: '#f0f0f0' }}>{f.title}</span>
                    <span style={{ display: 'block', fontSize: '12.5px', color: '#9a9a9a', lineHeight: 1.45, marginTop: '2px' }}>{f.desc}</span>
                  </span>
                </a>
              ))}
            </div>
          )}
        </div>
        {NAV_LINKS.map(link => (
          <a key={link.href} href={link.href} className="nav-link" style={linkStyle}>{link.label}</a>
        ))}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <a
          href="/#scan"
          className="navbar-cta"
          style={{ background: '#e63946', fontSize: '13px', fontWeight: 600, color: '#fff', padding: '8px 18px', borderRadius: '8px', letterSpacing: '0.02em', textDecoration: 'none', whiteSpace: 'nowrap' }}
          onClick={() => { setMenuOpen(false); focusScanSoon() }}
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
          style={{ background: 'none', border: '1px solid #2a2a2a', borderRadius: '8px', color: '#fff', width: '40px', height: '40px', cursor: 'pointer', fontSize: '18px', lineHeight: 1, alignItems: 'center', justifyContent: 'center' }}
        >
          {menuOpen ? '✕' : '☰'}
        </button>
      </div>

      {menuOpen && (
        <div
          id="mobile-menu"
          className="mobile-menu"
          style={{ position: 'absolute', top: '60px', left: 0, right: 0, maxHeight: 'calc(100vh - 60px)', overflowY: 'auto', background: '#0b0b0b', borderBottom: '1px solid #1a1a1a', padding: '8px 16px 16px', display: 'flex', flexDirection: 'column', gap: '2px' }}
        >
          <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', color: '#8a8a8a', textTransform: 'uppercase', padding: '10px 8px 4px' }}>Features</div>
          {FEATURES.map(f => (
            <a key={f.title} href={f.href} onClick={() => setMenuOpen(false)} className="features-item" style={{ padding: '10px 8px' }}>
              <Icon name={f.icon} />
              <span style={{ fontSize: '15px', color: '#e0e0e0' }}>{f.title}</span>
            </a>
          ))}
          <div style={{ height: '1px', background: '#1a1a1a', margin: '8px 0' }} />
          {[...NAV_LINKS, { label: 'Analyze a page', href: '/#scan' }].map(link => (
            <a key={link.href + link.label} href={link.href} onClick={() => setMenuOpen(false)}
              style={{ ...linkStyle, fontSize: '15px', padding: '12px 8px', color: '#e0e0e0' }}>
              {link.label}
            </a>
          ))}
        </div>
      )}

      <style>{`
        .nav-link:hover { color: #fff !important; }
        .navbar-menu-btn { display: none; }
        .features-menu { position: absolute; top: calc(100% + 10px); left: 50%; transform: translateX(-50%);
          width: min(640px, calc(100vw - 32px)); display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px;
          background: #111; border: 1px solid #262626; border-radius: 14px; padding: 12px; box-shadow: 0 18px 50px rgba(0,0,0,0.55); }
        .features-item { display: flex; gap: 12px; align-items: flex-start; padding: 12px; border-radius: 10px; text-decoration: none; }
        .features-item:hover, .features-item:focus-visible { background: #1a1a1a; }
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
