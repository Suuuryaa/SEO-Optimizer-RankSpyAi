function MetaRow({ label, value, ideal, color = '#fff' }) {
  const len = value ? String(value).length : 0
  return (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
        <span style={{ fontSize: '11px', fontWeight: 700, color: '#606060', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          {label}
        </span>
        {ideal && (
          <span style={{ fontSize: '11px', color: '#606060' }}>
            {len} chars{ideal && ` · ideal: ${ideal}`}
          </span>
        )}
      </div>
      <div
        style={{
          background: '#111',
          border: '1px solid #2a2a2a',
          borderRadius: '6px',
          padding: '10px 14px',
          fontSize: '13px',
          color: value ? color : '#444',
          wordBreak: 'break-word',
        }}
      >
        {value || <em style={{ color: '#444' }}>Not found</em>}
      </div>
    </div>
  )
}

function TagChip({ tag }) {
  return (
    <span
      style={{
        background: 'rgba(230,57,70,0.1)',
        border: '1px solid rgba(230,57,70,0.25)',
        color: '#e63946',
        fontSize: '12px',
        fontWeight: 600,
        padding: '4px 10px',
        borderRadius: '6px',
        display: 'inline-block',
      }}
    >
      {tag}
    </span>
  )
}

export default function ContentTab({ data }) {
  const cq = data.content_quality || {}

  return (
    <div className="fade-in">
      {/* Title / Meta / H1 */}
      <div
        style={{
          background: '#161616',
          border: '1px solid #2a2a2a',
          borderRadius: '12px',
          padding: '20px',
          marginBottom: '16px',
        }}
      >
        <div style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '16px' }}>
          PAGE META
        </div>
        <MetaRow label="Title" value={data.title} ideal="50–60 chars" color="#fff" />
        <MetaRow label="Meta Description" value={data.meta_description} ideal="120–160 chars" color="#a0a0a0" />

        {/* H1 tags */}
        <div>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#606060', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '8px' }}>
            H1 TAGS ({data.h1_tags?.length ?? 0})
          </div>
          {data.h1_tags && data.h1_tags.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {data.h1_tags.map((h, i) => (
                <div
                  key={i}
                  style={{
                    background: '#111',
                    border: '1px solid #2a2a2a',
                    borderLeft: '3px solid #e63946',
                    borderRadius: '6px',
                    padding: '10px 14px',
                    fontSize: '13px',
                    color: '#fff',
                  }}
                >
                  {h}
                </div>
              ))}
            </div>
          ) : (
            <div style={{ color: '#444', fontSize: '13px', fontStyle: 'italic' }}>No H1 tags found</div>
          )}
        </div>
      </div>

      {/* Content quality */}
      {Object.keys(cq).length > 0 && (
        <div
          style={{
            background: '#161616',
            border: '1px solid #2a2a2a',
            borderRadius: '12px',
            padding: '20px',
            marginBottom: '16px',
          }}
        >
          <div style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '16px' }}>
            CONTENT QUALITY
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '10px' }}>
            {Object.entries(cq).map(([k, v]) => (
              <div
                key={k}
                style={{
                  background: '#111',
                  border: '1px solid #2a2a2a',
                  borderRadius: '8px',
                  padding: '12px',
                }}
              >
                <div style={{ fontSize: '10px', color: '#606060', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '6px' }}>
                  {k.replace(/_/g, ' ')}
                </div>
                <div style={{ fontSize: '14px', color: '#fff', fontWeight: 600 }}>
                  {typeof v === 'boolean' ? (v ? '✅ Yes' : '❌ No') : String(v)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Keyword signals */}
      <div
        style={{
          background: '#161616',
          border: '1px solid #2a2a2a',
          borderRadius: '12px',
          padding: '20px',
        }}
      >
        <div style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '16px' }}>
          KEYWORD: <span style={{ color: '#e63946' }}>"{data.keyword}"</span>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {data.keyword_in_title && <TagChip tag="In Title ✓" />}
          {data.keyword_in_meta && <TagChip tag="In Meta ✓" />}
          {data.keyword_in_h1 && <TagChip tag="In H1 ✓" />}
          <span style={{ fontSize: '13px', color: '#a0a0a0', alignSelf: 'center' }}>
            {data.keyword_count} occurrences · {data.keyword_density}% density
          </span>
        </div>
      </div>
    </div>
  )
}
