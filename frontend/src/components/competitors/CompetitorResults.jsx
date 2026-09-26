function scoreColor(score) {
  if (score >= 80) return '#22c55e'
  if (score >= 60) return '#f97316'
  return '#e63946'
}

function ScoreBar({ score }) {
  const color = scoreColor(score)
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <div
        style={{
          flex: 1,
          height: '6px',
          background: '#222',
          borderRadius: '3px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${score}%`,
            height: '100%',
            background: color,
            borderRadius: '3px',
            transition: 'width 0.6s ease',
          }}
        />
      </div>
      <span style={{ fontSize: '13px', fontWeight: 700, color, minWidth: '32px', textAlign: 'right' }}>
        {score}
      </span>
    </div>
  )
}

function RankBadge({ rank }) {
  const colors = { 1: '#ffd700', 2: '#c0c0c0', 3: '#cd7f32' }
  const bg = colors[rank] || '#333'
  const isMedal = rank <= 3
  return (
    <div
      style={{
        width: '32px',
        height: '32px',
        borderRadius: '50%',
        background: isMedal ? bg : '#222',
        border: `2px solid ${isMedal ? bg : '#333'}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 800,
        fontSize: '13px',
        color: isMedal ? '#000' : '#888',
        flexShrink: 0,
      }}
    >
      {rank}
    </div>
  )
}

function CompetitorCard({ comp, rank }) {
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
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
        <RankBadge rank={rank} />
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {comp.title || comp.url || 'Unknown'}
          </div>
          <div style={{ fontSize: '11px', color: '#606060', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {comp.url}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '20px', fontWeight: 900, color: scoreColor(comp.seo_score ?? 0), lineHeight: 1 }}>
            {comp.seo_score ?? '—'}
          </div>
          <div style={{ fontSize: '9px', color: '#606060', letterSpacing: '0.06em' }}>SEO SCORE</div>
        </div>
      </div>

      <ScoreBar score={comp.seo_score ?? 0} />

      {/* Quick stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginTop: '12px' }}>
        {[
          { label: 'Words', val: comp.word_count?.toLocaleString() },
          { label: 'Links', val: (comp.internal_links ?? 0) + (comp.external_links ?? 0) },
          { label: 'KW Density', val: comp.keyword_density != null ? `${comp.keyword_density}%` : '—' },
        ].map(({ label, val }) => (
          <div key={label} style={{ background: '#111', borderRadius: '6px', padding: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>{val ?? '—'}</div>
            <div style={{ fontSize: '10px', color: '#606060' }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Keyword flags */}
      <div style={{ display: 'flex', gap: '6px', marginTop: '10px', flexWrap: 'wrap' }}>
        {comp.keyword_in_title && (
          <span style={{ fontSize: '10px', background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.25)', color: '#22c55e', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
            KW in Title
          </span>
        )}
        {comp.keyword_in_meta && (
          <span style={{ fontSize: '10px', background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.25)', color: '#3b82f6', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
            KW in Meta
          </span>
        )}
        {comp.keyword_in_h1 && (
          <span style={{ fontSize: '10px', background: 'rgba(168,85,247,0.1)', border: '1px solid rgba(168,85,247,0.25)', color: '#a855f7', padding: '2px 8px', borderRadius: '4px', fontWeight: 600 }}>
            KW in H1
          </span>
        )}
      </div>
    </div>
  )
}

function normalizeComp(c) {
  return {
    url: c.url ?? c.URL ?? '',
    title: c.title ?? c['Venue Name'] ?? c.url ?? c.URL ?? '',
    seo_score: c.seo_score ?? c['SEO Score'] ?? 0,
    word_count: c.word_count ?? c['Word Count'] ?? null,
    internal_links: c.internal_links ?? c['Internal Links'] ?? 0,
    external_links: c.external_links ?? c['External Links'] ?? 0,
    keyword_density: c.keyword_density ?? c['Keyword Density'] ?? null,
    keyword_in_title: c.keyword_in_title ?? c['Keyword in Title'] ?? false,
    keyword_in_meta: c.keyword_in_meta ?? c['Keyword in Meta'] ?? false,
    keyword_in_h1: c.keyword_in_h1 ?? c['Keyword in H1'] ?? false,
  }
}

export default function CompetitorResults({ data }) {
  // data may be array of competitors or an object with a competitors key
  const raw = Array.isArray(data) ? data : (data?.competitors ?? data?.results ?? [])
  const competitors = raw.map(normalizeComp)

  if (!competitors || competitors.length === 0) {
    return (
      <div
        style={{
          background: '#161616',
          border: '1px solid #2a2a2a',
          borderRadius: '12px',
          padding: '48px',
          textAlign: 'center',
          color: '#606060',
          marginTop: '24px',
        }}
      >
        <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔍</div>
        <div style={{ fontSize: '18px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>No Competitors Found</div>
        <div style={{ fontSize: '13px' }}>Try a different URL or keyword to find competitor data.</div>
      </div>
    )
  }

  const sorted = [...competitors].sort((a, b) => (b.seo_score ?? 0) - (a.seo_score ?? 0))

  return (
    <div style={{ marginTop: '24px' }}>
      {/* Leaderboard header */}
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
          COMPETITOR LEADERBOARD
        </div>

        {/* Table rows */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
          {/* Header row */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '40px 1fr 100px 100px 80px',
              gap: '12px',
              padding: '8px 12px',
              borderBottom: '1px solid #222',
            }}
          >
            {['#', 'URL', 'SEO Score', 'Words', 'Density'].map((h) => (
              <div key={h} style={{ fontSize: '10px', fontWeight: 700, color: '#606060', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{h}</div>
            ))}
          </div>

          {sorted.map((comp, i) => (
            <div
              key={i}
              style={{
                display: 'grid',
                gridTemplateColumns: '40px 1fr 100px 100px 80px',
                gap: '12px',
                padding: '10px 12px',
                borderBottom: i < sorted.length - 1 ? '1px solid #1a1a1a' : 'none',
                alignItems: 'center',
              }}
            >
              <RankBadge rank={i + 1} />
              <div style={{ overflow: 'hidden' }}>
                <div style={{ fontSize: '12px', color: '#fff', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {comp.title || comp.url}
                </div>
                <div style={{ fontSize: '10px', color: '#606060', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {comp.url}
                </div>
              </div>
              <div style={{ fontSize: '14px', fontWeight: 800, color: scoreColor(comp.seo_score ?? 0) }}>
                {comp.seo_score ?? '—'}
              </div>
              <div style={{ fontSize: '12px', color: '#a0a0a0' }}>
                {comp.word_count?.toLocaleString() ?? '—'}
              </div>
              <div style={{ fontSize: '12px', color: '#a0a0a0' }}>
                {comp.keyword_density != null ? `${comp.keyword_density}%` : '—'}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Competitor cards grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
        {sorted.map((comp, i) => (
          <CompetitorCard key={i} comp={comp} rank={i + 1} />
        ))}
      </div>
    </div>
  )
}
