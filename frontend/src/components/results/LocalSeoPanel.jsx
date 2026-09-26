export default function LocalSeoPanel({ data }) {
  if (!data) return null

  const {
    local_score = 0,
    nap = {},
    local_schema = {},
    geo_signals = {},
    google_maps_embed = false,
    local_checks = [],
    quick_fixes = [],
  } = data

  // Only show if score < 80 or any check fails
  const anyFail = local_checks.some(c => !c.pass)
  if (local_score >= 80 && !anyFail) return null

  function scoreColor(s) {
    if (s >= 70) return '#22c55e'
    if (s >= 40) return '#f97316'
    return '#e63946'
  }

  const color = scoreColor(local_score)

  const statChips = [
    {
      label: 'Phone',
      val: nap.phone_found ? '✓' : '✗',
      pass: nap.phone_found,
    },
    {
      label: 'Address',
      val: nap.address_found ? '✓' : '✗',
      pass: nap.address_found,
    },
    {
      label: 'Local Schema',
      val: local_schema.has_local_business ? '✓' : '✗',
      pass: local_schema.has_local_business,
    },
  ]

  return (
    <div style={{ background: '#111', border: '1px solid #222', borderRadius: '12px', overflow: 'hidden' }}>

      {/* Header */}
      <div style={{ background: '#161616', padding: '14px 20px', borderBottom: '1px solid #1e1e1e', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>Local SEO</span>
          <span style={{ fontSize: '11px', color: '#555', marginLeft: '8px' }}>NAP, schema & geo signals</span>
        </div>
        {/* Score badge */}
        <div style={{
          background: `${color}18`,
          border: `1px solid ${color}44`,
          borderRadius: '8px',
          padding: '6px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}>
          <span style={{ fontSize: '22px', fontWeight: 900, color, lineHeight: 1 }}>{local_score}</span>
          <span style={{ fontSize: '10px', color: '#555', fontWeight: 700 }}>/100</span>
        </div>
      </div>

      <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

        {/* NAP stat chips */}
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {statChips.map(chip => (
            <div key={chip.label} style={{
              background: chip.pass ? 'rgba(34,197,94,0.08)' : 'rgba(230,57,70,0.08)',
              border: `1px solid ${chip.pass ? 'rgba(34,197,94,0.25)' : 'rgba(230,57,70,0.25)'}`,
              borderRadius: '8px',
              padding: '8px 18px',
              textAlign: 'center',
              minWidth: '80px',
            }}>
              <div style={{ fontSize: '10px', color: '#555', letterSpacing: '0.06em', marginBottom: '3px', fontWeight: 600 }}>{chip.label}</div>
              <div style={{ fontSize: '16px', fontWeight: 900, color: chip.pass ? '#22c55e' : '#e63946' }}>{chip.val}</div>
            </div>
          ))}
          {/* Maps chip */}
          <div style={{
            background: google_maps_embed ? 'rgba(34,197,94,0.08)' : 'rgba(230,57,70,0.08)',
            border: `1px solid ${google_maps_embed ? 'rgba(34,197,94,0.25)' : 'rgba(230,57,70,0.25)'}`,
            borderRadius: '8px',
            padding: '8px 18px',
            textAlign: 'center',
            minWidth: '80px',
          }}>
            <div style={{ fontSize: '10px', color: '#555', letterSpacing: '0.06em', marginBottom: '3px', fontWeight: 600 }}>Maps</div>
            <div style={{ fontSize: '16px', fontWeight: 900, color: google_maps_embed ? '#22c55e' : '#e63946' }}>{google_maps_embed ? '✓' : '✗'}</div>
          </div>
          {/* City mention chip */}
          <div style={{
            background: geo_signals.city_mentions?.length > 0 ? 'rgba(34,197,94,0.08)' : 'rgba(230,57,70,0.08)',
            border: `1px solid ${geo_signals.city_mentions?.length > 0 ? 'rgba(34,197,94,0.25)' : 'rgba(230,57,70,0.25)'}`,
            borderRadius: '8px',
            padding: '8px 18px',
            textAlign: 'center',
            minWidth: '80px',
          }}>
            <div style={{ fontSize: '10px', color: '#555', letterSpacing: '0.06em', marginBottom: '3px', fontWeight: 600 }}>City Mention</div>
            <div style={{ fontSize: '16px', fontWeight: 900, color: geo_signals.city_mentions?.length > 0 ? '#22c55e' : '#e63946' }}>
              {geo_signals.city_mentions?.length > 0 ? '✓' : '✗'}
            </div>
          </div>
        </div>

        {/* Local Checks list */}
        {local_checks.length > 0 && (
          <div>
            <div style={{ fontSize: '11px', color: '#555', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '8px' }}>LOCAL CHECKS</div>
            <div style={{ background: '#0e0e0e', border: '1px solid #1a1a1a', borderRadius: '8px', overflow: 'hidden' }}>
              {local_checks.map((check, i) => {
                const dotColor = check.pass ? '#22c55e' : '#e63946'
                const statusLabel = check.pass ? 'OK' : 'Error'
                return (
                  <div key={i} style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr auto auto',
                    gap: '16px',
                    alignItems: 'center',
                    padding: '11px 16px',
                    borderBottom: i < local_checks.length - 1 ? '1px solid #181818' : 'none',
                  }}>
                    <span style={{ fontSize: '13px', color: '#c8c8c8' }}>{check.label}</span>
                    <span style={{ fontSize: '10px', color: '#444', fontWeight: 600, whiteSpace: 'nowrap' }}>{check.importance}</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '5px', minWidth: '56px', justifyContent: 'flex-end' }}>
                      <span style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: dotColor, flexShrink: 0 }} />
                      <span style={{ fontSize: '11px', color: dotColor, fontWeight: 700, letterSpacing: '0.03em' }}>{statusLabel}</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Quick fixes */}
        {quick_fixes.length > 0 && (
          <div>
            <div style={{ fontSize: '11px', color: '#555', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '8px' }}>QUICK FIXES</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {quick_fixes.map((fix, i) => (
                <div key={i} style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                  <span style={{ color: '#e63946', fontWeight: 900, fontSize: '14px', lineHeight: 1.4, flexShrink: 0 }}>→</span>
                  <span style={{ fontSize: '13px', color: '#c0c0c0', lineHeight: 1.5 }}>{fix}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Not a local business note */}
        <div style={{
          background: '#0e0e0e',
          border: '1px solid #1a1a1a',
          borderRadius: '8px',
          padding: '10px 14px',
          display: 'flex',
          gap: '8px',
          alignItems: 'flex-start',
        }}>
          <span style={{ fontSize: '12px', color: '#444', flexShrink: 0, lineHeight: 1.5 }}>ℹ</span>
          <span style={{ fontSize: '12px', color: '#444', lineHeight: 1.6 }}>
            <strong style={{ color: '#555' }}>NOT A LOCAL BUSINESS?</strong> Skip this section if your site does not serve a specific local area.
          </span>
        </div>

      </div>
    </div>
  )
}
