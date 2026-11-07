import { useState } from 'react'
import { scoreColor } from '../../lib/score'

const SUBSCORES = [
  { key: 'crawlers', label: 'AI search crawlers' },
  { key: 'citability', label: 'Citability' },
  { key: 'eeat', label: 'E-E-A-T' },
  { key: 'schema', label: 'Structured data' },
  { key: 'llmstxt', label: 'LLMs.txt' },
]

function SubBar({ label, weight, score }) {
  const color = scoreColor(score)
  return (
    <div style={{ marginBottom: '14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', marginBottom: '5px' }}>
        <span style={{ fontSize: '12px', color: 'var(--text-body)', fontWeight: 600 }}>
          {label}
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 400, marginLeft: '6px' }}>
            weight {Math.round(weight * 100)}%
          </span>
        </span>
        <span style={{ fontSize: '12px', fontWeight: 700, color }}>{score}</span>
      </div>
      <div style={{ height: '5px', background: '#222', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${Math.max(0, Math.min(100, score))}%`, background: color, borderRadius: '3px', transition: 'width 0.6s ease' }} />
      </div>
    </div>
  )
}

function Chip({ tone, children }) {
  const tones = {
    ok: { bg: 'rgba(74,222,128,0.1)', border: 'rgba(74,222,128,0.3)', color: '#4ade80' },
    bad: { bg: 'rgba(230,57,70,0.1)', border: 'rgba(230,57,70,0.35)', color: '#ff6b75' },
    neutral: { bg: '#1a1a1a', border: '#2a2a2a', color: '#c0c0c0' },
  }
  const t = tones[tone] || tones.neutral
  return (
    <span style={{ background: t.bg, border: `1px solid ${t.border}`, borderRadius: '4px', padding: '3px 8px', fontSize: '11px', color: t.color, fontWeight: 600 }}>
      {children}
    </span>
  )
}

// Accepts {crawlers: [{name, status, category}]} and the older {allowed: [], blocked: []}.
function crawlerList(crawlers) {
  if (!crawlers) return []
  const fromItem = c => (typeof c === 'string'
    ? { name: c, status: 'allowed', category: null }
    : { name: c?.name || c?.user_agent || '?', status: c?.status, category: c?.category || null })
  if (Array.isArray(crawlers.crawlers)) return crawlers.crawlers.map(fromItem)
  if (Array.isArray(crawlers)) return crawlers.map(fromItem)
  return [
    ...(crawlers.allowed || []).map(n => ({ name: n, status: 'allowed', category: null })),
    ...(crawlers.blocked || []).map(n => ({ name: n, status: 'blocked', category: null })),
  ]
}

function CrawlerGroup({ title, note, items, blockedTone }) {
  if (items.length === 0) return null
  return (
    <div style={{ marginBottom: '12px' }}>
      <h4 style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.08em', margin: '0 0 4px', textTransform: 'uppercase' }}>{title}</h4>
      {note && <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: '0 0 8px' }}>{note}</p>}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {items.map(c => (
          <Chip key={c.name} tone={c.status === 'blocked' ? blockedTone : c.status === 'allowed' ? 'ok' : 'neutral'}>
            {c.status === 'blocked' ? '✗' : c.status === 'allowed' ? '✓' : '–'} {c.name}
          </Chip>
        ))}
      </div>
    </div>
  )
}

export default function GeoScorePanel({ geo }) {
  const [showTooltip, setShowTooltip] = useState(false)

  if (!geo) return null
  if (geo.error) {
    return (
      <div style={{ background: '#111', border: '1px solid #222', borderRadius: '12px', padding: '16px 20px', fontSize: '13px', color: 'var(--text-body)' }}>
        The AI-visibility (GEO) check isn't available right now. The rest of your results are unaffected.
      </div>
    )
  }

  const { score = 0, band, breakdown, crawlers, llmstxt } = geo
  const mainColor = scoreColor(score)
  const list = crawlerList(crawlers)
  const hasCategories = list.some(c => c.category)
  const search = list.filter(c => c.category === 'search')
  const training = list.filter(c => c.category === 'training')
  const other = list.filter(c => c.category !== 'search' && c.category !== 'training')
  const llmsInfoOnly = breakdown?.llmstxt?.weight === 0
  const snip = geo.snippet_controls
  const snippetBlocked = !!snip && (snip.nosnippet === true || snip.max_snippet === 0)

  return (
    <section aria-labelledby="geo-h" style={{ background: '#111', border: '1px solid #222', borderRadius: '12px', padding: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px', marginBottom: '20px' }}>
        <div>
          <h2 id="geo-h" style={{ fontSize: '16px', color: '#fff', fontWeight: 800, margin: 0 }}>AI visibility (GEO)</h2>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '6px' }}>
            <span style={{ fontSize: '36px', fontWeight: 800, color: mainColor, lineHeight: 1 }}>{score}</span>
            <span style={{ fontSize: '13px', color: mainColor, fontWeight: 600 }}>{band}</span>
          </div>
        </div>
        <div style={{ position: 'relative' }}>
          <button
            type="button"
            aria-label="About the GEO score"
            aria-expanded={showTooltip}
            aria-controls="geo-tooltip"
            onClick={() => setShowTooltip(v => !v)}
            onBlur={() => setShowTooltip(false)}
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
            style={{
              width: '22px', height: '22px', borderRadius: '50%', padding: 0,
              background: '#1e1e1e', border: '1px solid #333',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '11px', color: 'var(--text-body)', cursor: 'pointer', fontWeight: 700,
            }}
          >?</button>
          {showTooltip && (
            <div id="geo-tooltip" role="tooltip" style={{
              position: 'absolute', right: 0, top: '28px', zIndex: 100,
              background: '#1e1e1e', border: '1px solid #333', borderRadius: '8px',
              padding: '10px 14px', width: '260px', maxWidth: '70vw', fontSize: '12px', color: 'var(--text-body)',
              lineHeight: 1.5, boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
            }}>
              Estimates how easily AI search tools like ChatGPT, Perplexity and Claude can read and cite your page.
            </div>
          )}
        </div>
      </div>

      {snippetBlocked && (
        <div role="note" style={{ background: 'rgba(230,57,70,0.08)', border: '1px solid rgba(230,57,70,0.35)', borderRadius: '8px', padding: '10px 14px', marginBottom: '16px', fontSize: '12px', color: '#f0c0c4', lineHeight: 1.5 }}>
          <strong style={{ color: '#ff6b75' }}>Snippets are switched off. </strong>
          {snip.nosnippet ? 'This page uses "nosnippet"' : 'This page sets "max-snippet:0"'}, so Google and AI search tools can't quote it in answers.
        </div>
      )}

      {breakdown && (
        <div style={{ marginBottom: '16px' }}>
          {SUBSCORES.filter(s => breakdown[s.key] && !(s.key === 'llmstxt' && llmsInfoOnly)).map(s => (
            <SubBar key={s.key} label={s.label} weight={breakdown[s.key].weight ?? 0} score={breakdown[s.key].score ?? 0} />
          ))}
        </div>
      )}

      {list.length > 0 && (
        <div style={{ background: '#0f0f0f', border: '1px solid #1e1e1e', borderRadius: '8px', padding: '14px 16px', marginBottom: '10px' }}>
          <h3 style={{ fontSize: '11px', color: 'var(--text-body)', fontWeight: 700, letterSpacing: '0.1em', margin: '0 0 10px' }}>
            AI CRAWLER ACCESS (robots.txt)
          </h3>
          {hasCategories ? (
            <>
              <CrawlerGroup title="AI search" note="These fetch pages to answer searches. Blocking them hides you from AI answers." items={search} blockedTone="bad" />
              <CrawlerGroup title="AI training" note="Blocking these is your choice and does not lower your score." items={training} blockedTone="neutral" />
              <CrawlerGroup title="Other" items={other} blockedTone="bad" />
            </>
          ) : (
            <CrawlerGroup title="Crawlers" items={list} blockedTone="bad" />
          )}
        </div>
      )}

      {llmstxt !== undefined && (
        <div style={{ background: '#0f0f0f', border: '1px solid #1e1e1e', borderRadius: '8px', padding: '12px 16px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span aria-hidden="true" style={{ fontSize: '18px', color: llmstxt?.exists ? '#4ade80' : (llmsInfoOnly ? '#8a8a8a' : '#ff6b75'), lineHeight: 1 }}>
            {llmstxt?.exists ? '✓' : (llmsInfoOnly ? 'i' : '✗')}
          </span>
          <div>
            <div style={{ fontSize: '12px', fontWeight: 700, color: llmstxt?.exists ? '#4ade80' : (llmsInfoOnly ? '#c0c0c0' : '#ff6b75') }}>
              /llms.txt {llmstxt?.exists ? 'found' : 'not found'}
            </div>
            {(llmsInfoOnly || !llmstxt?.exists) && (
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                {llmsInfoOnly
                  ? 'For information only: no major AI search tool is known to use it, so it does not affect your score.'
                  : 'Add /llms.txt to improve AI visibility'}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}
