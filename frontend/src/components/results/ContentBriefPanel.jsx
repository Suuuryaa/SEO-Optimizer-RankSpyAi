export default function ContentBriefPanel({ brief }) {
  if (!brief) return null

  const {
    word_count_target, word_count_gap, competitor_avg_words, competitor_avg_score,
    topic_gaps, heading_suggestions, quick_wins, ai_brief,
  } = brief

  return (
    <div style={{ background: '#111', border: '1px solid #222', borderRadius: '12px', overflow: 'hidden' }}>
      <div style={{ background: '#161616', padding: '14px 20px', borderBottom: '1px solid #1e1e1e' }}>
        <span style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>Content Brief</span>
        <span style={{ fontSize: '11px', color: '#555', marginLeft: '8px' }}>AI gap analysis vs top competitors</span>
      </div>

      <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>

        {/* Stats row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
          {[
            { label: 'Target word count', val: word_count_target?.toLocaleString(), color: '#e63946' },
            { label: 'Words to add', val: `+${word_count_gap?.toLocaleString() || 0}`, color: '#f97316' },
            { label: 'Competitor avg', val: `${competitor_avg_words?.toLocaleString() || 0} words / ${Math.round(competitor_avg_score || 0)} score`, color: '#a0a0a0' },
          ].map(stat => (
            <div key={stat.label} style={{ background: '#0e0e0e', border: '1px solid #1a1a1a', borderRadius: '8px', padding: '12px 14px' }}>
              <div style={{ fontSize: '18px', fontWeight: 900, color: stat.color, marginBottom: '4px' }}>{stat.val}</div>
              <div style={{ fontSize: '11px', color: '#555', fontWeight: 600 }}>{stat.label}</div>
            </div>
          ))}
        </div>

        {/* AI brief */}
        {ai_brief && (
          <div>
            <div style={{ fontSize: '11px', color: '#555', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '10px' }}>AI CONTENT STRATEGY</div>
            <div style={{ fontSize: '13px', color: '#b0b0b0', lineHeight: 1.7, background: '#0e0e0e', border: '1px solid #1a1a1a', borderRadius: '8px', padding: '14px 16px' }}>
              {ai_brief}
            </div>
          </div>
        )}

        {/* Quick wins */}
        {quick_wins?.length > 0 && (
          <div>
            <div style={{ fontSize: '11px', color: '#555', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '10px' }}>QUICK WINS</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {quick_wins.map((w, i) => (
                <div key={i} style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                  <span style={{ color: '#e63946', fontWeight: 900, fontSize: '14px', lineHeight: 1.4, flexShrink: 0 }}>→</span>
                  <span style={{ fontSize: '13px', color: '#c0c0c0', lineHeight: 1.5 }}>{w}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          {/* Missing topics */}
          {topic_gaps?.length > 0 && (
            <div>
              <div style={{ fontSize: '11px', color: '#555', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '10px' }}>MISSING TOPICS</div>
              <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                {topic_gaps.slice(0, 12).map((t, i) => (
                  <span key={i} style={{
                    fontSize: '11px', padding: '3px 10px', borderRadius: '99px',
                    background: 'rgba(230,57,70,0.08)', border: '1px solid rgba(230,57,70,0.2)', color: '#e63946', fontWeight: 600,
                  }}>
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Heading suggestions */}
          {heading_suggestions?.length > 0 && (
            <div>
              <div style={{ fontSize: '11px', color: '#555', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '10px' }}>SUGGESTED HEADINGS</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {heading_suggestions.slice(0, 6).map((h, i) => (
                  <div key={i} style={{ fontSize: '12px', color: '#a0a0a0', display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span style={{ color: '#333', fontWeight: 700, fontFamily: 'monospace' }}>H{i === 0 ? '1' : '2'}</span>
                    <span>{h}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
