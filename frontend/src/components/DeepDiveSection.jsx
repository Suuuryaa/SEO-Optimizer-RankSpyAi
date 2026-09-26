export default function DeepDiveSection() {
  const sectionStyle = {
    display: 'flex',
    gap: '48px',
    alignItems: 'center',
    flexWrap: 'wrap',
    padding: '48px 0',
    borderBottom: '1px solid #1a1a1a',
  }
  const mockCard = {
    background: '#161616',
    border: '1px solid #2a2a2a',
    borderRadius: '10px',
    padding: '24px',
    minHeight: '180px',
    flex: '0 0 300px',
    maxWidth: '340px',
  }
  const textSide = {
    flex: 1,
    minWidth: '220px',
  }
  const sectionTitle = {
    fontSize: '22px',
    fontWeight: 800,
    color: '#fff',
    marginBottom: '10px',
    lineHeight: 1.3,
  }
  const subtitle = {
    fontSize: '14px',
    color: '#606060',
    marginBottom: '18px',
  }
  const bullet = {
    fontSize: '13px',
    color: '#a0a0a0',
    marginBottom: '8px',
    display: 'flex',
    alignItems: 'flex-start',
    gap: '8px',
  }
  const dot = {
    width: '4px',
    height: '4px',
    borderRadius: '50%',
    background: '#e63946',
    marginTop: '7px',
    flexShrink: 0,
  }

  function StatusDot({ color }) {
    return <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: color, marginRight: '8px', flexShrink: 0 }} />
  }

  function MetricRow({ label, value, status }) {
    const colors = { pass: '#22c55e', warn: '#f97316', fail: '#e63946' }
    const icons = { pass: '✓', warn: '⚠', fail: '✗' }
    return (
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '9px 0', borderBottom: '1px solid #1e1e1e' }}>
        <span style={{ fontSize: '13px', color: '#ccc' }}>{label}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '12px', color: '#a0a0a0' }}>{value}</span>
          <span style={{ color: colors[status], fontWeight: 700, fontSize: '13px' }}>{icons[status]}</span>
        </div>
      </div>
    )
  }

  const bullets1 = ['Overly short or missing meta titles', 'Missing canonical links', 'Robots noindex / nofollow issues', 'Inconsistent language declarations']
  const bullets2 = ['Pages with too little text (< 300 words)', 'Images without descriptive ALT text', 'Missing keyword in H1 heading', 'Low keyword density or over-optimization']
  const bullets3 = ['Missing or multiple H1 headings', 'Too few internal links', 'Duplicate anchor text issues', 'Missing external authority links']

  return (
    <div style={{ padding: '60px 0 20px' }}>
      <div style={{ textAlign: 'center', marginBottom: '48px' }}>
        <div style={{ fontSize: '11px', color: '#e63946', fontWeight: 700, letterSpacing: '0.12em', marginBottom: '8px' }}>DEEP DIVE</div>
        <div style={{ fontSize: '28px', fontWeight: 800, color: '#fff' }}>What We Check</div>
      </div>

      {/* Row 1: mockup left, text right */}
      <div style={sectionStyle}>
        <div style={mockCard}>
          <div style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '14px' }}>META TAGS</div>
          {[
            { tag: '<title>', status: '#22c55e' },
            { tag: '<description>', status: '#e63946' },
            { tag: '<canonical>', status: '#f97316' },
          ].map(r => (
            <div key={r.tag} style={{ display: 'flex', alignItems: 'center', padding: '9px 0', borderBottom: '1px solid #1e1e1e' }}>
              <StatusDot color={r.status} />
              <span style={{ fontSize: '13px', color: '#a0a0a0', fontFamily: 'monospace' }}>{r.tag}</span>
            </div>
          ))}
        </div>
        <div style={textSide}>
          <div style={sectionTitle}><span style={{ color: '#e63946' }}>Meta</span> information</div>
          <div style={subtitle}>Help search engines understand your pages</div>
          {bullets1.map(b => <div key={b} style={bullet}><span style={dot} />{b}</div>)}
        </div>
      </div>

      {/* Row 2: text left, mockup right */}
      <div style={{ ...sectionStyle, flexDirection: 'row-reverse' }}>
        <div style={mockCard}>
          <div style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '14px' }}>CONTENT METRICS</div>
          <MetricRow label="Word count" value="247 words" status="warn" />
          <MetricRow label="Missing ALT" value="3 images" status="fail" />
          <MetricRow label="Keyword density" value="0.8%" status="pass" />
        </div>
        <div style={textSide}>
          <div style={sectionTitle}><span style={{ color: '#e63946' }}>Content</span> Quality</div>
          <div style={subtitle}>Create content that performs</div>
          {bullets2.map(b => <div key={b} style={bullet}><span style={dot} />{b}</div>)}
        </div>
      </div>

      {/* Row 3: mockup left, text right */}
      <div style={{ ...sectionStyle, borderBottom: 'none' }}>
        <div style={mockCard}>
          <div style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '14px' }}>LINK STRUCTURE</div>
          {[
            { label: 'Internal: 14 links', status: 'pass' },
            { label: 'External: 3 links', status: 'pass' },
            { label: 'H1 headings: 1', status: 'pass' },
            { label: 'H2 headings: 0', status: 'warn' },
          ].map(item => {
            const colors = { pass: '#22c55e', warn: '#f97316' }
            const icons = { pass: '✓', warn: '⚠' }
            return (
              <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '9px 0', borderBottom: '1px solid #1e1e1e' }}>
                <span style={{ fontSize: '13px', color: '#a0a0a0' }}>{item.label}</span>
                <span style={{ color: colors[item.status], fontWeight: 700 }}>{icons[item.status]}</span>
              </div>
            )
          })}
        </div>
        <div style={textSide}>
          <div style={sectionTitle}><span style={{ color: '#e63946' }}>Link</span> Structure</div>
          <div style={subtitle}>Improve crawlability for search engines</div>
          {bullets3.map(b => <div key={b} style={bullet}><span style={dot} />{b}</div>)}
        </div>
      </div>
    </div>
  )
}
