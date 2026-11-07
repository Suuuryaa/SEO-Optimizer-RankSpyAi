import { priorityBadge, whyText } from '../../lib/score'

export function PriorityBadge({ priority }) {
  const b = priorityBadge(priority)
  return (
    <span style={{
      fontSize: '10px', fontWeight: 800, letterSpacing: '0.04em', padding: '3px 10px', borderRadius: '99px',
      background: b.bg, color: b.color, border: `1px solid ${b.border}`, whiteSpace: 'nowrap', display: 'inline-block',
    }}>
      {b.label}
    </span>
  )
}

// "Your next 3 fixes": issue → fix → why, for the three highest-priority tasks.
export default function NextFixes({ recs }) {
  const top = (recs || []).slice(0, 3)
  if (top.length === 0) return null
  return (
    <section aria-labelledby="next-fixes-h" style={{ background: '#111', border: '1px solid #222', borderRadius: '12px', padding: '20px' }}>
      <h2 id="next-fixes-h" style={{ fontSize: '16px', fontWeight: 800, color: '#fff', margin: '0 0 14px' }}>
        Your next {top.length === 1 ? 'fix' : `${top.length} fixes`}
      </h2>
      <ol style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {top.map((rec, i) => (
          <li key={i} style={{ background: '#161616', border: '1px solid #2a2a2a', borderRadius: '10px', padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', flexWrap: 'wrap', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', fontWeight: 800, color: 'var(--text-muted)' }}>{i + 1}.</span>
              <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#f0f0f0', margin: 0, flex: '1 1 200px' }}>{rec.issue}</h3>
              <PriorityBadge priority={rec.priority} />
            </div>
            {rec.fix && (
              <p style={{ fontSize: '13px', color: '#d0d0d0', lineHeight: 1.55, margin: '0 0 4px' }}>
                <strong style={{ color: '#fff' }}>How to fix: </strong>{rec.fix}
              </p>
            )}
            {whyText(rec.impact) && (
              <p style={{ fontSize: '12px', color: 'var(--text-body)', lineHeight: 1.55, margin: 0 }}>
                <strong style={{ color: 'var(--text-body)' }}>Why it matters: </strong>{whyText(rec.impact)}
              </p>
            )}
          </li>
        ))}
      </ol>
    </section>
  )
}
