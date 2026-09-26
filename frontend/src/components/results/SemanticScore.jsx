export default function SemanticScore({ semantic }) {
  if (!semantic || semantic.semantic_score == null) return null

  const score = semantic.semantic_score
  const label = semantic.semantic_label || ''
  const hf    = semantic.hf_available

  const color = score >= 75 ? '#22c55e' : score >= 50 ? '#f97316' : score >= 30 ? '#eab308' : '#e63946'
  const deg   = Math.round(score * 3.6)

  return (
    <div style={{
      background: '#111', border: '1px solid #222', borderRadius: '12px',
      padding: '20px 24px', display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap',
    }}>
      {/* Mini donut */}
      <div style={{
        width: '72px', height: '72px', borderRadius: '50%', flexShrink: 0,
        background: `conic-gradient(${color} 0deg ${deg}deg, #1e1e1e ${deg}deg 360deg)`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{
          width: '50px', height: '50px', borderRadius: '50%', background: '#111',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <span style={{ fontSize: '16px', fontWeight: 900, color }}>{score}</span>
        </div>
      </div>

      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>Semantic Relevance</span>
          {!hf && (
            <span style={{ fontSize: '10px', color: '#555', background: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: '4px', padding: '1px 6px' }}>
              fallback mode
            </span>
          )}
        </div>
        <div style={{ fontSize: '12px', color, fontWeight: 600, marginBottom: '6px' }}>{label}</div>
        <div style={{ height: '4px', background: '#1e1e1e', borderRadius: '99px', overflow: 'hidden', maxWidth: '300px' }}>
          <div style={{ width: `${score}%`, height: '100%', background: color, borderRadius: '99px', transition: 'width 0.8s ease' }} />
        </div>
        {semantic.best_chunk && (
          <div style={{ fontSize: '11px', color: '#555', marginTop: '8px', fontStyle: 'italic', lineHeight: 1.5 }}>
            Best matching section: "{semantic.best_chunk.slice(0, 100)}…"
          </div>
        )}
      </div>

      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        <div style={{ fontSize: '10px', color: '#555', letterSpacing: '0.08em', fontWeight: 700 }}>POWERED BY</div>
        <div style={{ fontSize: '11px', color: '#a0a0a0', fontWeight: 600 }}>
          {hf ? 'HuggingFace MiniLM' : 'Keyword analysis'}
        </div>
      </div>
    </div>
  )
}
