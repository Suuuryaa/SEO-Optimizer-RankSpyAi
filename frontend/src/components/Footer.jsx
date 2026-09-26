function scrollTo(id) {
  const el = document.getElementById(id)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  else window.scrollTo({ top: 0, behavior: 'smooth' })
}

export default function Footer({ onLegal, onContact }) {
  const colStyle = { display: 'flex', flexDirection: 'column', gap: '10px', minWidth: '130px' }
  const colHeader = { fontSize: '10px', fontWeight: 700, color: '#606060', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '4px' }
  const linkStyle = { fontSize: '13px', color: '#a0a0a0', textDecoration: 'none', cursor: 'pointer', background: 'none', border: 'none', textAlign: 'left', padding: 0, fontFamily: 'inherit' }

  const cols = [
    {
      title: 'Tools',
      links: [
        { label: 'SEO Analyzer', id: 'section-top' },
        { label: 'Competitor Finder', id: 'section-top' },
        { label: 'Keyword Analysis', id: 'section-features' },
        { label: 'Technical Audit', id: 'section-features' },
      ],
    },
    {
      title: 'Features',
      links: [
        { label: 'Meta Tag Check', id: 'section-features' },
        { label: 'Content Quality', id: 'section-features' },
        { label: 'Link Structure', id: 'section-features' },
        { label: 'AI / GEO Signals', id: 'section-features' },
      ],
    },
    {
      title: 'About',
      links: [
        { label: 'How It Works', id: 'section-how' },
        { label: 'FAQ', id: 'section-faq' },
        { label: 'Score Guide', id: 'section-scale' },
        { label: 'Privacy Policy', id: null, legal: 'Privacy Policy' },
      ],
    },
    {
      title: 'Legal',
      links: [
        { label: 'Terms of Service', id: null, legal: 'Terms of Service' },
        { label: 'Privacy Policy', id: null, legal: 'Privacy Policy' },
        { label: 'Cookie Policy', id: null, legal: 'Cookie Policy' },
      ],
    },
  ]

  return (
    <footer style={{ background: '#0d0d0d', borderTop: '1px solid #1a1a1a', padding: '48px 24px 32px' }}>
      <div style={{ maxWidth: '900px', margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '40px' }}>
          <div>
            <span style={{ fontSize: '18px', fontWeight: 800, color: '#fff', letterSpacing: '0.04em' }}>
              RANKSPY <span style={{ color: '#e63946' }}>AI</span>
            </span>
          </div>
          <span style={{ fontSize: '13px', color: '#606060' }}>Free SEO analysis powered by AI</span>
        </div>

        <div style={{ display: 'flex', gap: '40px', flexWrap: 'wrap', marginBottom: '40px' }}>
          {cols.map(col => (
            <div key={col.title} style={colStyle}>
              <div style={colHeader}>{col.title}</div>
              {col.links.map(link => (
                <button
                  key={link.label}
                  style={linkStyle}
                  onClick={() => link.legal ? onLegal(link.legal) : link.id ? scrollTo(link.id) : null}
                  onMouseEnter={e => e.currentTarget.style.color = '#fff'}
                  onMouseLeave={e => e.currentTarget.style.color = '#a0a0a0'}
                >
                  {link.label}
                </button>
              ))}
            </div>
          ))}
        </div>

        {/* Disclaimer */}
        <div style={{ background: '#111', border: '1px solid #1a1a1a', borderRadius: '8px', padding: '14px 18px', marginBottom: '24px', fontSize: '12px', color: '#555', lineHeight: 1.6 }}>
          <span style={{ fontWeight: 700, color: '#444' }}>Disclaimer: </span>
          RankSpy AI provides SEO analysis for informational purposes only. Results are estimates based on on-page factors and do not guarantee search engine rankings. Search engine algorithms change frequently and actual rankings may vary. We are not affiliated with Google, Bing, or any search engine.
        </div>

        {/* Contact CTA */}
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <button
            onClick={() => onContact && onContact()}
            style={{
              background: 'transparent',
              border: '1px solid #333',
              borderRadius: '100px',
              padding: '12px 28px',
              fontSize: '13px',
              color: '#fff',
              cursor: 'pointer',
              fontFamily: 'inherit',
              transition: 'border-color 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.borderColor = '#606060')}
            onMouseLeave={e => (e.currentTarget.style.borderColor = '#333')}
          >
            Contact us
          </button>
        </div>

        <div style={{ borderTop: '1px solid #1a1a1a', paddingTop: '20px', textAlign: 'center' }}>
          <span style={{ fontSize: '12px', color: '#333' }}>© 2026 RankSpy AI · Free SEO Tools</span>
        </div>
      </div>
    </footer>
  )
}
