import { useState } from 'react'

// Links use "/#section" so they work from every page (/, /faq).
const COLUMNS = [
  {
    title: 'Product',
    links: [
      { label: 'Free SEO check', href: '/#scan' },
      { label: 'Competitor comparison', href: '/#scan' },
      { label: 'AI visibility (GEO)', href: '/#features' },
      { label: 'Score guide', href: '/#score-guide' },
    ],
  },
  {
    title: 'Fix-it tools',
    links: [
      { label: 'AI meta tag writer', href: '/#features' },
      { label: 'Schema generator', href: '/#features' },
      { label: 'Local SEO check', href: '/#features' },
      { label: 'JS rendering & deep crawl', href: '/#scan' },
    ],
  },
  {
    title: 'Help',
    links: [
      { label: 'How it works', href: '/#how-it-works' },
      { label: 'FAQ', href: '/faq' },
      { label: 'Contact', contact: true },
    ],
  },
]

const LEGAL = ['Terms of Service', 'Privacy Policy', 'Cookie Policy']

function QuickCheck() {
  const [url, setUrl] = useState('')
  function go(e) {
    e.preventDefault()
    const v = url.trim()
    // Opens the scan form with the address filled in; the visitor presses Analyze
    window.location.assign(v ? `/?url=${encodeURIComponent(v)}&mode=analyze#scan` : '/#scan')
  }
  return (
    <form onSubmit={go} className="footer-check" role="search" aria-label="Quick SEO check">
      <label htmlFor="footer-url" className="sr-only">Website URL</label>
      <input
        id="footer-url" type="text" inputMode="url" autoComplete="url" placeholder="Website URL"
        value={url} onChange={e => setUrl(e.target.value)}
      />
      <button type="submit">Check</button>
    </form>
  )
}

export default function Footer({ onLegal, onContact }) {
  const linkStyle = { fontSize: '14px', color: '#a8a8a8', textDecoration: 'none', cursor: 'pointer', background: 'none', border: 'none', textAlign: 'left', padding: 0, fontFamily: 'inherit' }

  return (
    <footer className="no-print" style={{ background: '#0b0b0b', borderTop: '1px solid #1a1a1a', padding: '56px 16px 28px' }}>
      <div style={{ maxWidth: '1088px', margin: '0 auto' }}>
        <div className="footer-top">
          {/* Brand + quick check */}
          <div style={{ minWidth: 0 }}>
            <a href="/" aria-label="RankSpy AI home" style={{ textDecoration: 'none' }}>
              <span style={{ fontSize: '18px', fontWeight: 800, color: '#fff', letterSpacing: '0.04em' }}>
                RANKSPY <span style={{ color: '#e63946' }}>AI</span>
              </span>
            </a>
            <QuickCheck />
            <p style={{ fontSize: '14px', color: '#9a9a9a', lineHeight: 1.6, margin: 0, maxWidth: '380px' }}>
              On-page SEO audits, AI-visibility checks and real Google competitor comparisons, in plain English.
            </p>
          </div>

          {/* Link columns */}
          <div className="footer-cols">
            {COLUMNS.map(col => (
              <nav key={col.title} aria-label={col.title}>
                <div className="footer-col-h">{col.title}</div>
                <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: '12px' }}>
                  {col.links.map(link => (
                    <li key={link.label}>
                      {link.href ? (
                        <a href={link.href} className="footer-link" style={linkStyle}>{link.label}</a>
                      ) : (
                        <button type="button" className="footer-link" style={linkStyle} onClick={() => onContact?.()}>{link.label}</button>
                      )}
                    </li>
                  ))}
                </ul>
              </nav>
            ))}
          </div>
        </div>

        <p style={{ fontSize: '12px', color: '#8a8a8a', lineHeight: 1.6, margin: '40px 0 0', maxWidth: '760px' }}>
          Scores and positions are estimates for information only and don&rsquo;t guarantee rankings.
          RankSpy AI is not affiliated with Google, Bing or any search engine.
        </p>

        {/* Bottom bar */}
        <div className="footer-bottom">
          <span>&copy; 2026 RankSpy AI. All rights reserved.</span>
          <span className="footer-legal">
            {LEGAL.map((name, i) => (
              <span key={name}>
                {i > 0 && <span aria-hidden="true" style={{ margin: '0 8px', color: '#555' }}>&bull;</span>}
                <button type="button" className="footer-link" style={{ ...linkStyle, fontSize: '13px', color: '#8a8a8a' }} onClick={() => onLegal(name)}>
                  {name}
                </button>
              </span>
            ))}
          </span>
        </div>
      </div>

      <style>{`
        .footer-link:hover { color: #fff !important; }
        .footer-top { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.4fr); gap: 48px; }
        .footer-cols { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 32px; }
        .footer-col-h { font-size: 12px; font-weight: 700; color: #e6e6e6; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 16px; }
        .footer-check { display: flex; align-items: center; gap: 6px; margin: 20px 0 16px; max-width: 380px;
          background: #141414; border: 1px solid #2a2a2a; border-radius: 12px; padding: 6px 6px 6px 14px; }
        .footer-check:focus-within { border-color: #e63946; }
        .footer-check input { flex: 1; min-width: 0; background: transparent; border: none; outline: none; color: #fff; font-size: 14px; font-family: inherit; }
        .footer-check input::placeholder { color: #777; }
        .footer-check button { background: #e63946; color: #fff; border: none; border-radius: 8px; padding: 10px 18px; font-weight: 700; font-size: 14px; cursor: pointer; font-family: inherit; }
        .footer-check button:hover { background: #d62f3c; }
        .footer-bottom { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;
          border-top: 1px solid #1a1a1a; margin-top: 24px; padding-top: 20px; font-size: 13px; color: #8a8a8a; }
        @media (max-width: 860px) {
          .footer-top { grid-template-columns: minmax(0, 1fr); gap: 36px; }
        }
        @media (max-width: 520px) {
          .footer-cols { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
      `}</style>
    </footer>
  )
}
