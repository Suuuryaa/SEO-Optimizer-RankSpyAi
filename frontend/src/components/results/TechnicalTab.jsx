function CheckTile({ label, value, description = '' }) {
  const pass = value === true
  const fail = value === false
  const warn = !pass && !fail

  let cls = 'check-warn'
  let icon = '⚠️'
  let statusLabel = 'UNKNOWN'
  let statusColor = '#eab308'

  if (pass) { cls = 'check-pass'; icon = '✅'; statusLabel = 'PASS'; statusColor = '#22c55e' }
  if (fail) { cls = 'check-fail'; icon = '❌'; statusLabel = 'FAIL'; statusColor = '#e63946' }

  return (
    <div
      className={`metric-card ${cls}`}
      style={{
        background: '#161616',
        border: '1px solid #2a2a2a',
        borderRadius: '10px',
        padding: '18px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '4px' }}>{label}</div>
          {description && (
            <div style={{ fontSize: '11px', color: '#606060' }}>{description}</div>
          )}
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '20px', lineHeight: 1, marginBottom: '4px' }}>{icon}</div>
          <div style={{ fontSize: '10px', fontWeight: 800, letterSpacing: '0.08em', color: statusColor }}>{statusLabel}</div>
        </div>
      </div>
    </div>
  )
}

function ValueTile({ label, value, description = '' }) {
  const hasValue = value !== null && value !== undefined && value !== ''
  return (
    <div
      className="metric-card"
      style={{
        background: '#161616',
        border: '1px solid #2a2a2a',
        borderRadius: '10px',
        padding: '18px',
      }}
    >
      <div style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '8px', textTransform: 'uppercase' }}>
        {label}
      </div>
      <div style={{ fontSize: '13px', color: hasValue ? '#fff' : '#444', wordBreak: 'break-all' }}>
        {hasValue ? String(value) : 'Not detected'}
      </div>
      {description && <div style={{ fontSize: '11px', color: '#606060', marginTop: '4px' }}>{description}</div>}
    </div>
  )
}

export default function TechnicalTab({ data }) {
  const tech = data.technical_seo || {}

  return (
    <div className="fade-in">
      <div style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '16px' }}>
        TECHNICAL CHECKS
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px', marginBottom: '24px' }}>
        <CheckTile label="HTTPS" value={tech.https} description="Secure connection" />
        <CheckTile label="Mobile Viewport" value={tech.mobile_viewport} description="Viewport meta tag present" />
        <CheckTile label="Schema Markup" value={tech.schema_markup} description="Structured data detected" />
        <CheckTile label="Canonical Tag" value={tech.canonical} description="Canonical URL set" />
        <CheckTile label="Open Graph Tags" value={tech.og_tags} description="Social sharing metadata" />
        {tech.hreflang !== undefined && (
          <CheckTile label="Hreflang" value={tech.hreflang} description="International targeting" />
        )}
        {tech.robots_txt !== undefined && (
          <CheckTile label="Robots.txt" value={tech.robots_txt} description="Crawl directives" />
        )}
        {tech.sitemap !== undefined && (
          <CheckTile label="Sitemap" value={tech.sitemap} description="XML sitemap present" />
        )}
      </div>

      {/* Additional technical fields */}
      {Object.keys(tech).some(k => typeof tech[k] !== 'boolean') && (
        <>
          <div style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '16px' }}>
            ADDITIONAL SIGNALS
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '12px' }}>
            {Object.entries(tech)
              .filter(([, v]) => typeof v !== 'boolean')
              .map(([k, v]) => (
                <ValueTile key={k} label={k.replace(/_/g, ' ')} value={v} />
              ))}
          </div>
        </>
      )}
    </div>
  )
}
