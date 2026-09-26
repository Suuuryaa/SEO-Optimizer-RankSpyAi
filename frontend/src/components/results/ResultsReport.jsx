import { useState } from 'react'
import SemanticScore from './SemanticScore'
import GeoScorePanel from './GeoScorePanel'
import MetaSuggestPanel from './MetaSuggestPanel'
import SchemaPanel from './SchemaPanel'
import RankTracker from '../RankTracker'
import LocalSeoPanel from './LocalSeoPanel'
import DeepCrawlPanel from './DeepCrawlPanel'
import { analyzeLocalSeo } from '../../api'

export default function ResultsReport({ data }) {
  const tech = data.technical_seo || {}
  const recs = data.recommendations || []

  const [localData, setLocalData] = useState(null)
  const [localLoading, setLocalLoading] = useState(false)
  const [localError, setLocalError] = useState(null)

  async function handleCheckLocalSeo() {
    setLocalLoading(true)
    setLocalError(null)
    try {
      const result = await analyzeLocalSeo({ url: data.url, keyword: data.keyword })
      setLocalData(result)
    } catch (err) {
      setLocalError('Local SEO check failed. Please try again.')
    } finally {
      setLocalLoading(false)
    }
  }

  function scoreColor(s) {
    if (s >= 70) return '#22c55e'
    if (s >= 40) return '#f97316'
    return '#e63946'
  }

  function pct(booleans) {
    const vals = booleans.map(b => (b ? 1 : 0))
    return Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 100)
  }

  const metaScore = pct([
    data.title_length >= 30 && data.title_length <= 60,
    data.meta_length >= 50 && data.meta_length <= 160,
    !!data.keyword_in_title,
    !!data.keyword_in_meta,
    !!tech.has_canonical,
    !tech.robots_noindex,
  ])

  const pageScore = pct([
    data.word_count >= 300,
    data.missing_alt === 0,
    !!data.keyword_in_h1,
    !!tech.has_schema,
    !!tech.mobile_viewport,
  ])

  const linkScore = pct([
    tech.h1_count === 1,
    tech.h2_count > 0,
    data.internal_links >= 2,
    data.external_links >= 1,
  ])

  const serverScore = pct([
    !!tech.https_enabled,
    !!tech.mobile_viewport,
    !!tech.has_lang,
    !!tech.has_og_title,
    !tech.robots_noindex,
  ])

  const keywordScore = pct([
    !!data.keyword_in_title,
    !!data.keyword_in_meta,
    !!data.keyword_in_h1,
    data.keyword_density > 0 && data.keyword_density < 5,
  ])

  const socialScore = pct([
    !!tech.has_og_title,
    !!tech.has_og_description,
    !!tech.has_og_image,
    !!tech.has_twitter_card,
    !!tech.has_schema,
  ])

  const categories = [
    { label: 'Meta data', score: metaScore },
    { label: 'Page quality', score: pageScore },
    { label: 'Link structure', score: linkScore },
    { label: 'Server config', score: serverScore },
    { label: 'Keyword usage', score: keywordScore },
    { label: 'Social / Schema', score: socialScore },
  ]

  const priorityOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }
  const sortedRecs = [...recs]
    .sort((a, b) => (priorityOrder[a.priority] ?? 99) - (priorityOrder[b.priority] ?? 99))
    .slice(0, 10)

  function badgeStyle(p) {
    if (p === 'CRITICAL' || p === 'HIGH') return { bg: 'rgba(230,57,70,0.12)', color: '#e63946', border: 'rgba(230,57,70,0.3)', label: 'Error' }
    if (p === 'MEDIUM') return { bg: 'rgba(234,179,8,0.12)', color: '#eab308', border: 'rgba(234,179,8,0.3)', label: 'Warning' }
    return { bg: 'rgba(59,130,246,0.12)', color: '#3b82f6', border: 'rgba(59,130,246,0.3)', label: 'Tip' }
  }

  function CheckItem({ label, value, pass, warn, importance }) {
    const status = pass === null ? 'info' : pass ? 'pass' : warn ? 'warn' : 'fail'
    const color = status === 'pass' ? '#22c55e' : status === 'warn' ? '#f97316' : status === 'info' ? '#555' : '#e63946'
    const statusLabel = status === 'pass' ? 'OK' : status === 'warn' ? 'Warning' : status === 'info' ? '—' : 'Error'

    return (
      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto auto', gap: '16px', alignItems: 'center', padding: '11px 18px', borderBottom: '1px solid #181818' }}>
        <div>
          <span style={{ fontSize: '13px', color: '#c8c8c8' }}>{label}</span>
          {value != null && (
            <span style={{ fontSize: '12px', color: '#555', marginLeft: '8px' }}>{value}</span>
          )}
        </div>
        {importance && (
          <span style={{ fontSize: '10px', color: '#444', fontWeight: 600, whiteSpace: 'nowrap' }}>{importance}</span>
        )}
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', minWidth: '64px', justifyContent: 'flex-end' }}>
          <span style={{
            display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%',
            background: color, flexShrink: 0
          }} />
          <span style={{ fontSize: '11px', color, fontWeight: 700, letterSpacing: '0.03em' }}>{statusLabel}</span>
        </div>
      </div>
    )
  }

  function CheckGroup({ title, score, checks }) {
    const c = scoreColor(score)
    const barDeg = Math.round(score * 3.6)
    return (
      <div style={{ background: '#111', border: '1px solid #222', borderRadius: '10px', overflow: 'hidden', marginBottom: '12px' }}>
        <div style={{ background: '#161616', padding: '13px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #222' }}>
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>{title}</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ width: '100px', height: '5px', background: '#252525', borderRadius: '99px', overflow: 'hidden' }}>
              <div style={{ width: `${score}%`, height: '100%', background: c, borderRadius: '99px', transition: 'width 0.8s ease' }} />
            </div>
            <span style={{ fontSize: '13px', color: c, fontWeight: 700, minWidth: '36px', textAlign: 'right' }}>{score}%</span>
          </div>
        </div>
        {checks}
      </div>
    )
  }

  const mainScore = data.seo_score ?? 0
  const scoreAngle = mainScore * 3.6

  return (
    <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* ── Semantic Relevance (HuggingFace) ── */}
      {data.semantic && <SemanticScore semantic={data.semantic} />}

      {/* ── Deep Crawl results (JS mode) ── */}
      {data.deep_crawl && <DeepCrawlPanel data={data.deep_crawl} />}

      {/* ── GEO Score (AI Visibility) ── */}
      {data.geo_score && <GeoScorePanel geo={data.geo_score} />}

      {/* ── Section 1: Score + Categories ── */}
      <div style={{ background: '#111', border: '1px solid #222', borderRadius: '12px', padding: '28px 32px' }}>
        <div style={{ display: 'flex', gap: '40px', flexWrap: 'wrap', alignItems: 'flex-start' }}>

          {/* Score donut */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px', flexShrink: 0 }}>
            <div style={{
              width: '140px', height: '140px', borderRadius: '50%',
              background: `conic-gradient(${scoreColor(mainScore)} 0deg ${scoreAngle}deg, #1e1e1e ${scoreAngle}deg 360deg)`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: `0 0 0 2px #111, 0 0 24px ${scoreColor(mainScore)}22`,
            }}>
              <div style={{
                width: '104px', height: '104px', borderRadius: '50%', background: '#111',
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1px',
              }}>
                <span style={{ fontSize: '34px', fontWeight: 900, color: scoreColor(mainScore), lineHeight: 1 }}>{mainScore}</span>
                <span style={{ fontSize: '9px', color: '#555', letterSpacing: '0.08em', fontWeight: 700 }}>of 100</span>
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#606060', letterSpacing: '0.1em', fontWeight: 700 }}>ON-PAGE SCORE</div>
              {data.score_band && (
                <div style={{ fontSize: '12px', color: scoreColor(mainScore), fontWeight: 700, marginTop: '4px', textTransform: 'capitalize' }}>{data.score_band}</div>
              )}
            </div>
          </div>

          {/* Category bars — 2-column grid */}
          <div style={{ flex: 1, minWidth: '260px' }}>
            <div style={{ fontSize: '11px', color: '#555', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '16px' }}>SCORE BREAKDOWN</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px 32px' }}>
              {categories.map(cat => (
                <div key={cat.label}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontSize: '12px', color: '#a0a0a0', fontWeight: 500 }}>{cat.label}</span>
                    <span style={{ fontSize: '12px', fontWeight: 800, color: scoreColor(cat.score) }}>{cat.score}%</span>
                  </div>
                  <div style={{ height: '5px', background: '#1e1e1e', borderRadius: '99px', overflow: 'hidden' }}>
                    <div style={{ width: `${cat.score}%`, height: '100%', background: scoreColor(cat.score), borderRadius: '99px', transition: 'width 0.8s ease' }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Section 2: Page Info Card ── */}
      <div style={{ background: '#111', border: '1px solid #222', borderRadius: '12px', padding: '22px' }}>
        <div style={{ fontSize: '11px', color: '#555', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '18px' }}>PAGE INFORMATION</div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '18px' }}>
          {[
            { label: 'Page title', value: data.title || 'Not found', bad: !data.title },
            { label: 'Meta description', value: data.meta_description || 'Not found', bad: !data.meta_description },
            { label: 'Page URL', value: data.url || '—', bad: false },
          ].map(row => (
            <div key={row.label} style={{ display: 'grid', gridTemplateColumns: '130px 1fr', gap: '12px', alignItems: 'flex-start' }}>
              <span style={{ fontSize: '12px', color: '#555', fontWeight: 600, paddingTop: '1px' }}>{row.label}</span>
              <span style={{ fontSize: '13px', color: row.bad ? '#e63946' : '#d0d0d0', wordBreak: 'break-all', lineHeight: 1.5 }}>{row.value}</span>
            </div>
          ))}
        </div>

        {/* Stat chips */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {[
            { label: 'Status', val: tech.https_enabled ? '200 OK' : 'HTTP', color: tech.https_enabled ? '#22c55e' : '#f97316', bg: tech.https_enabled ? 'rgba(34,197,94,0.1)' : 'rgba(249,115,22,0.1)', border: tech.https_enabled ? 'rgba(34,197,94,0.25)' : 'rgba(249,115,22,0.25)' },
            { label: 'Words', val: data.word_count?.toLocaleString() ?? '—', color: '#a0a0a0', bg: '#161616', border: '#2a2a2a' },
            { label: 'Language', val: tech.lang_attribute || '—', color: '#a0a0a0', bg: '#161616', border: '#2a2a2a' },
            { label: 'H1 tags', val: tech.h1_count ?? '—', color: tech.h1_count === 1 ? '#22c55e' : '#f97316', bg: '#161616', border: '#2a2a2a' },
            { label: 'Mobile', val: tech.mobile_viewport ? 'Yes' : 'No', color: tech.mobile_viewport ? '#22c55e' : '#e63946', bg: '#161616', border: '#2a2a2a' },
            { label: 'Canonical', val: tech.has_canonical ? 'Yes' : 'No', color: tech.has_canonical ? '#22c55e' : '#e63946', bg: '#161616', border: '#2a2a2a' },
          ].map(chip => (
            <div key={chip.label} style={{ background: chip.bg, border: `1px solid ${chip.border}`, borderRadius: '8px', padding: '8px 14px', textAlign: 'center', minWidth: '64px' }}>
              <div style={{ fontSize: '10px', color: '#555', letterSpacing: '0.06em', marginBottom: '3px', fontWeight: 600 }}>{chip.label}</div>
              <div style={{ fontSize: '13px', fontWeight: 800, color: chip.color }}>{String(chip.val)}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Section 3: TO-DO / Task List ── */}
      {sortedRecs.length > 0 && (
        <div style={{ background: '#111', border: '1px solid #222', borderRadius: '12px', overflow: 'hidden' }}>
          <div style={{ background: '#161616', padding: '14px 20px', borderBottom: '1px solid #222', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>Tasks sorted by priority</span>
            <span style={{
              fontSize: '11px', fontWeight: 700, color: '#555', background: '#1e1e1e',
              border: '1px solid #2a2a2a', padding: '1px 8px', borderRadius: '99px',
            }}>{sortedRecs.length}</span>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#0e0e0e' }}>
                  {['Status', 'Issue', 'Action'].map(h => (
                    <th key={h} style={{ padding: '9px 16px', fontSize: '10px', color: '#555', fontWeight: 700, letterSpacing: '0.08em', textAlign: 'left', borderBottom: '1px solid #1e1e1e', textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedRecs.map((rec, i) => {
                  const b = badgeStyle(rec.priority)
                  return (
                    <tr key={i} style={{ borderBottom: '1px solid #181818' }}>
                      <td style={{ padding: '12px 16px', whiteSpace: 'nowrap', width: '80px' }}>
                        <span style={{ fontSize: '10px', fontWeight: 800, letterSpacing: '0.04em', padding: '3px 10px', borderRadius: '99px', background: b.bg, color: b.color, border: `1px solid ${b.border}` }}>
                          {b.label}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontSize: '13px', color: '#e0e0e0', fontWeight: 600, marginBottom: '3px' }}>{rec.issue}</div>
                        <div style={{ fontSize: '12px', color: '#555' }}>{rec.fix}</div>
                      </td>
                      <td style={{ padding: '12px 16px', fontSize: '12px', color: '#707070', minWidth: '160px' }}>{rec.impact}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── AI Tools: Meta Generator + Schema ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
        <MetaSuggestPanel url={data.url} keyword={data.keyword} currentTitle={data.title} currentMeta={data.meta_description} />
        <SchemaPanel url={data.url} keyword={data.keyword} />
      </div>

      {/* ── Local SEO ── */}
      <div>
        {!localData && (
          <button
            onClick={handleCheckLocalSeo}
            disabled={localLoading}
            style={{
              width: '100%',
              padding: '12px 20px',
              background: localLoading ? '#1a1a1a' : '#161616',
              border: '1px solid #2a2a2a',
              borderRadius: '10px',
              color: localLoading ? '#555' : '#a0a0a0',
              fontSize: '13px',
              fontWeight: 600,
              cursor: localLoading ? 'default' : 'pointer',
              letterSpacing: '0.02em',
              transition: 'background 0.15s, color 0.15s',
            }}
          >
            {localLoading ? 'Checking local SEO signals\u2026' : '\uD83D\uDCCD Check Local SEO'}
          </button>
        )}
        {localError && (
          <div style={{ fontSize: '12px', color: '#e63946', marginTop: '8px', textAlign: 'center' }}>{localError}</div>
        )}
        {localData && <LocalSeoPanel data={localData} />}
        {localData && localData.local_score >= 80 && !localData.local_checks?.some(c => !c.pass) && (
          <div style={{ background: '#111', border: '1px solid #222', borderRadius: '10px', padding: '14px 20px', display: 'flex', gap: '10px', alignItems: 'center' }}>
            <span style={{ color: '#22c55e', fontSize: '16px' }}>&#x2713;</span>
            <span style={{ fontSize: '13px', color: '#22c55e', fontWeight: 600 }}>Local SEO looks great — score {localData.local_score}/100, all checks passing.</span>
          </div>
        )}
      </div>

      {/* ── Section 4: Detailed Checks ── */}
      <div style={{ marginTop: '8px' }}>
        <div style={{ fontSize: '11px', color: '#555', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '16px' }}>DETAILED CHECKS</div>

        <CheckGroup title="Meta Data" score={metaScore} checks={
          <>
            <CheckItem label="Page title" value={data.title ? `${data.title_length} chars` : 'Not found'} pass={data.title_length >= 30 && data.title_length <= 60} importance="Very important" />
            <CheckItem label="Meta description" value={data.meta_description ? `${data.meta_length} chars` : 'Not found'} pass={data.meta_length >= 50 && data.meta_length <= 160} importance="Very important" />
            <CheckItem label="Keyword in title" value={null} pass={!!data.keyword_in_title} importance="Very important" />
            <CheckItem label="Keyword in meta description" value={null} pass={!!data.keyword_in_meta} importance="Important" />
            <CheckItem label="Canonical URL" value={tech.canonical_url ? 'Set' : 'Not set'} pass={!!tech.has_canonical} importance="Important" />
            <CheckItem label="Robots meta" value={tech.robots_noindex ? 'noindex' : 'Indexable'} pass={!tech.robots_noindex} importance="Very important" />
            <CheckItem label="Language declaration" value={tech.lang_attribute || null} pass={!!tech.has_lang} importance="Nice to have" />
          </>
        } />

        <CheckGroup title="Page Quality" score={pageScore} checks={
          <>
            <CheckItem label="Word count" value={`${data.word_count ?? 0} words`} pass={data.word_count >= 300} importance="Important" />
            <CheckItem label="Images — ALT attributes" value={data.missing_alt === 0 ? 'All present' : `${data.missing_alt} missing`} pass={data.missing_alt === 0} importance="Important" />
            <CheckItem label="Keyword in H1" value={null} pass={!!data.keyword_in_h1} importance="Very important" />
            <CheckItem label="Structured data / Schema" value={tech.has_schema ? 'Detected' : 'Not found'} pass={!!tech.has_schema} importance="Nice to have" />
            <CheckItem label="Mobile viewport" value={tech.viewport_content || (tech.mobile_viewport ? 'Set' : 'Missing')} pass={!!tech.mobile_viewport} importance="Very important" />
            <CheckItem label="H1 headings" value={`${tech.h1_count ?? 0} found`} pass={tech.h1_count === 1} importance="Very important" />
            <CheckItem label="Keyword density" value={data.keyword_density != null ? `${data.keyword_density}%` : '—'} pass={data.keyword_density > 0 && data.keyword_density < 5} warn={data.keyword_density >= 5} importance="Important" />
          </>
        } />

        <CheckGroup title="Link Structure" score={linkScore} checks={
          <>
            <CheckItem label="Internal links" value={`${data.internal_links ?? 0} found`} pass={data.internal_links >= 2} importance="Important" />
            <CheckItem label="External links" value={`${data.external_links ?? 0} found`} pass={data.external_links >= 1} importance="Nice to have" />
            <CheckItem label="H2 headings" value={`${tech.h2_count ?? 0} found`} pass={tech.h2_count > 0} importance="Important" />
            <CheckItem label="H3 headings" value={`${tech.h3_count ?? 0} found`} pass={null} importance="Nice to have" />
          </>
        } />

        <CheckGroup title="Social & Technical" score={socialScore} checks={
          <>
            <CheckItem label="HTTPS / SSL" value={tech.https_enabled ? 'Secure' : 'Not secure'} pass={!!tech.https_enabled} importance="Very important" />
            <CheckItem label="Open Graph title" value={tech.has_og_title ? 'Present' : 'Missing'} pass={!!tech.has_og_title} importance="Nice to have" />
            <CheckItem label="Open Graph description" value={tech.has_og_description ? 'Present' : 'Missing'} pass={!!tech.has_og_description} importance="Nice to have" />
            <CheckItem label="Open Graph image" value={tech.has_og_image ? 'Present' : 'Missing'} pass={!!tech.has_og_image} importance="Nice to have" />
            <CheckItem label="Twitter Card" value={tech.has_twitter_card ? 'Present' : 'Missing'} pass={!!tech.has_twitter_card} importance="Nice to have" />
            <CheckItem label="Structured data" value={tech.has_schema ? 'Found' : 'Not found'} pass={!!tech.has_schema} importance="Nice to have" />
          </>
        } />
      </div>

      {/* ── Rank Tracker ── */}
      <RankTracker url={data.url} keyword={data.keyword} />
    </div>
  )
}
