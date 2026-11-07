const REASONS = {
  meta_noindex: 'The page has a "noindex" robots meta tag, so Google will not list it.',
  x_robots_noindex: 'The server sends an "X-Robots-Tag: noindex" header, so Google will not list it.',
  robots_txt_blocked: "Your robots.txt file blocks Googlebot from this page.",
  canonical_elsewhere: 'The canonical tag points Google to a different URL',
}

export default function IndexabilityBanner({ indexability, uncapped }) {
  if (indexability?.indexable !== false) return null
  const reasons = Array.isArray(indexability.reasons) ? indexability.reasons : []
  return (
    <section
      role="alert"
      aria-labelledby="indexability-h"
      style={{ background: 'rgba(230,57,70,0.1)', border: '1px solid rgba(230,57,70,0.45)', borderRadius: '12px', padding: '18px 20px' }}
    >
      <h2 id="indexability-h" style={{ fontSize: '15px', fontWeight: 800, color: '#ff6b75', margin: '0 0 8px' }}>
        Fix indexing first: Google can't index this page
      </h2>
      {reasons.length > 0 && (
        <ul style={{ margin: '0 0 8px', paddingLeft: '18px', color: '#e0e0e0', fontSize: '13px', lineHeight: 1.6 }}>
          {reasons.map((r, i) => {
            const base = REASONS[r?.code] || 'Something on this page tells search engines not to index it.'
            const extra = r?.code === 'canonical_elsewhere' && indexability.canonical_url ? `: ${indexability.canonical_url}` : (r?.code === 'canonical_elsewhere' ? '.' : '')
            return <li key={i} style={{ wordBreak: 'break-word' }}>{base}{extra}</li>
          })}
        </ul>
      )}
      {typeof uncapped === 'number' && (
        <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-body)' }}>
          Your on-page score would be <strong style={{ color: '#fff' }}>{uncapped}</strong> once Google can index this page.
        </p>
      )}
    </section>
  )
}
