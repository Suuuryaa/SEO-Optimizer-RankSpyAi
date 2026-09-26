import { useState } from 'react'

function scoreColor(score) {
  if (score >= 70) return '#4ade80'
  if (score >= 40) return '#fb923c'
  return '#e63946'
}

function SubBar({ label, weight, score, color }) {
  return (
    <div style={{ marginBottom: '14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
        <span style={{ fontSize: '12px', color: '#a0a0a0', fontWeight: 600 }}>
          {label}
          <span style={{ fontSize: '10px', color: '#555', fontWeight: 400, marginLeft: '6px' }}>
            weight {Math.round(weight * 100)}%
          </span>
        </span>
        <span style={{ fontSize: '12px', fontWeight: 700, color: color }}>{score}</span>
      </div>
      <div style={{ height: '5px', background: '#222', borderRadius: '3px', overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${score}%`,
            background: color,
            borderRadius: '3px',
            transition: 'width 0.6s ease',
          }}
        />
      </div>
    </div>
  )
}

export default function GeoScorePanel({ geo }) {
  const [showTooltip, setShowTooltip] = useState(false)

  if (!geo) return null

  const { score, band, breakdown, crawlers, citability, llmstxt, eeat } = geo

  const mainColor = scoreColor(score)

  return (
    <div
      style={{
        background: '#111',
        border: '1px solid #222',
        borderRadius: '12px',
        padding: '24px 28px',
        marginTop: '16px',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div>
            <div style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.1em' }}>
              GEO SCORE — AI Visibility
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '4px' }}>
              <span style={{ fontSize: '36px', fontWeight: 800, color: mainColor, lineHeight: 1 }}>{score}</span>
              <span style={{ fontSize: '13px', color: mainColor, fontWeight: 600 }}>{band}</span>
            </div>
          </div>
        </div>
        {/* Info tooltip */}
        <div style={{ position: 'relative' }}>
          <span
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
            style={{
              width: '20px', height: '20px', borderRadius: '50%',
              background: '#1e1e1e', border: '1px solid #333',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '11px', color: '#606060', cursor: 'default', fontWeight: 700,
            }}
          >?</span>
          {showTooltip && (
            <div style={{
              position: 'absolute', right: 0, top: '26px', zIndex: 100,
              background: '#1e1e1e', border: '1px solid #333', borderRadius: '8px',
              padding: '10px 14px', width: '260px', fontSize: '12px', color: '#a0a0a0',
              lineHeight: 1.5, boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
            }}>
              Measures how visible your page is to AI search engines like ChatGPT, Perplexity, and Claude.
            </div>
          )}
        </div>
      </div>

      {/* Sub-score bars */}
      <div style={{ marginBottom: '20px' }}>
        {breakdown && (
          <>
            <SubBar
              label="AI Crawlers"
              weight={breakdown.crawlers?.weight ?? 0.3}
              score={breakdown.crawlers?.score ?? 0}
              color={scoreColor(breakdown.crawlers?.score ?? 0)}
            />
            <SubBar
              label="Citability"
              weight={breakdown.citability?.weight ?? 0.25}
              score={breakdown.citability?.score ?? 0}
              color={scoreColor(breakdown.citability?.score ?? 0)}
            />
            <SubBar
              label="E-E-A-T"
              weight={breakdown.eeat?.weight ?? 0.25}
              score={breakdown.eeat?.score ?? 0}
              color={scoreColor(breakdown.eeat?.score ?? 0)}
            />
            <SubBar
              label="LLMs.txt"
              weight={breakdown.llmstxt?.weight ?? 0.1}
              score={breakdown.llmstxt?.score ?? 0}
              color={scoreColor(breakdown.llmstxt?.score ?? 0)}
            />
          </>
        )}
      </div>

      {/* Crawlers detail */}
      {crawlers && (
        <div
          style={{
            background: '#0f0f0f',
            border: '1px solid #1e1e1e',
            borderRadius: '8px',
            padding: '14px 16px',
            marginBottom: '10px',
          }}
        >
          <div style={{ fontSize: '10px', color: '#555', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '10px' }}>
            AI CRAWLER ACCESS
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {(crawlers.allowed || []).map(bot => (
              <span
                key={bot}
                style={{
                  background: 'rgba(74,222,128,0.1)',
                  border: '1px solid rgba(74,222,128,0.3)',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  fontSize: '11px',
                  color: '#4ade80',
                  fontWeight: 600,
                }}
              >
                ✓ {bot}
              </span>
            ))}
            {(crawlers.blocked || []).map(bot => (
              <span
                key={bot}
                style={{
                  background: 'rgba(230,57,70,0.1)',
                  border: '1px solid rgba(230,57,70,0.3)',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  fontSize: '11px',
                  color: '#e63946',
                  fontWeight: 600,
                }}
              >
                ✗ {bot}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* LLMs.txt detail */}
      {llmstxt !== undefined && (
        <div
          style={{
            background: '#0f0f0f',
            border: '1px solid #1e1e1e',
            borderRadius: '8px',
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <span style={{ fontSize: '18px', color: llmstxt?.exists ? '#4ade80' : '#e63946', lineHeight: 1 }}>
            {llmstxt?.exists ? '✓' : '✗'}
          </span>
          <div>
            <div style={{ fontSize: '12px', fontWeight: 700, color: llmstxt?.exists ? '#4ade80' : '#e63946' }}>
              /llms.txt {llmstxt?.exists ? 'found' : 'not found'}
            </div>
            {!llmstxt?.exists && (
              <div style={{ fontSize: '11px', color: '#555', marginTop: '2px' }}>
                Add /llms.txt to improve AI visibility
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
