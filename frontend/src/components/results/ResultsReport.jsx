import { useState } from 'react'
import GeoScorePanel from './GeoScorePanel'
import MetaSuggestPanel from './MetaSuggestPanel'
import SchemaPanel from './SchemaPanel'
import RankTracker from '../RankTracker'
import LocalSeoPanel from './LocalSeoPanel'
import DeepCrawlPanel from './DeepCrawlPanel'
import NextFixes, { PriorityBadge } from './NextFixes'
import IndexabilityBanner from './IndexabilityBanner'
import { analyzeLocalSeo } from '../../api'
import { scoreBand, verdictFor, sortRecs, whyText, relativeTime } from '../../lib/score'

const TASKS_PREVIEW = 10

const STATUS = {
  pass: { color: '#22c55e', label: 'OK' },
  warn: { color: '#f97316', label: 'Needs attention' },
  fail: { color: '#ff6b75', label: 'Missing' },
  optional: { color: '#8a8a8a', label: 'Optional' },
  info: { color: '#8a8a8a', label: '—' },
}

const MISSING_TITLE = ['', 'No title found']
const MISSING_META = ['', 'No meta description found']

function hasTitle(data) {
  if (typeof data.has_title === 'boolean') return data.has_title
  return !MISSING_TITLE.includes(String(data.title ?? '').trim())
}

function hasMeta(data) {
  if (typeof data.has_meta_description === 'boolean') return data.has_meta_description
  return !MISSING_META.includes(String(data.meta_description ?? '').trim())
}

// Keyword check: exact = pass; all words present but not as a phrase = warn.
function kwCheck(data, flag, field) {
  if (!String(data.keyword ?? '').trim()) return { status: 'info', value: 'No keyword given' }
  const m = data.keyword_match?.[field]
  if (m === 'all_tokens') return { status: 'warn', value: 'All words present, not as an exact phrase' }
  if (m === 'exact' || flag) return { status: 'pass', value: 'Found' }
  return { status: 'fail', value: 'Not found' }
}

function densityCheck(data) {
  const d = Number(data.keyword_density)
  if (!String(data.keyword ?? '').trim() || data.keyword_density == null || Number.isNaN(d)) {
    return { status: 'info', value: '—' }
  }
  if (data.keyword_stuffing === true || d > 3.5) return { status: 'fail', value: `${d}% (possible stuffing)` }
  if (d > 2.5) return { status: 'warn', value: `${d}% (a little high)` }
  if (d >= 0.5) return { status: 'pass', value: `${d}%` }
  if (d > 0) return { status: 'warn', value: `${d}% (low)` }
  return { status: 'fail', value: '0% (not used in the text)' }
}

// Every check appears in exactly one group.
function buildChecks(data) {
  const tech = data.technical_seo || {}
  const titleOk = hasTitle(data)
  const metaOk = hasMeta(data)
  const tl = Number(data.title_length) || 0
  const ml = Number(data.meta_length) || 0
  const wc = Number(data.word_count) || 0
  const noindex = data.indexability?.indexable === false || !!tech.robots_noindex
  const kwTitle = kwCheck(data, data.keyword_in_title, 'title')
  const kwMeta = kwCheck(data, data.keyword_in_meta, 'meta')
  const kwH1 = kwCheck(data, data.keyword_in_h1, 'h1')
  const h1 = tech.h1_count

  return [
    {
      title: 'Meta data',
      checks: [
        { label: 'Page title', importance: 'Very important', ...(!titleOk ? { status: 'fail', value: 'Missing' } : tl >= 30 && tl <= 60 ? { status: 'pass', value: `${tl} chars` } : { status: 'warn', value: `${tl} chars (aim for 30–60)` }) },
        { label: 'Meta description', importance: 'Very important', ...(!metaOk ? { status: 'fail', value: 'Missing' } : ml >= 120 && ml <= 160 ? { status: 'pass', value: `${ml} chars` } : { status: 'warn', value: `${ml} chars (aim for 120–160)` }) },
        { label: 'Keyword in title', importance: 'Very important', ...kwTitle },
        { label: 'Keyword in meta description', importance: 'Important', ...kwMeta },
        { label: 'Canonical URL', importance: 'Important', status: tech.has_canonical ? 'pass' : 'warn', value: tech.has_canonical ? 'Set' : 'Not set' },
        { label: 'Robots meta / indexing', importance: 'Very important', status: noindex ? 'fail' : 'pass', value: noindex ? 'Not indexable' : 'Indexable' },
      ],
    },
    {
      title: 'Content',
      checks: [
        { label: 'Word count', importance: 'Important', status: wc >= 300 ? 'pass' : wc >= 150 ? 'warn' : 'fail', value: `${wc.toLocaleString()} words` },
        { label: 'Keyword in H1', importance: 'Very important', ...kwH1 },
        { label: 'Keyword density', importance: 'Important', ...densityCheck(data) },
        { label: 'H1 headings', importance: 'Very important', status: h1 === 1 ? 'pass' : !h1 ? 'fail' : 'warn', value: `${h1 ?? 0} found` },
        { label: 'Image alt text', importance: 'Important', status: !data.missing_alt ? 'pass' : 'warn', value: !data.missing_alt ? 'All present' : `${data.missing_alt} missing` },
      ],
    },
    {
      title: 'Links & headings',
      checks: [
        { label: 'Internal links', importance: 'Important', status: data.internal_links >= 2 ? 'pass' : 'warn', value: `${data.internal_links ?? 0} found` },
        { label: 'External links', importance: 'Nice to have', status: data.external_links >= 1 ? 'pass' : 'optional', value: `${data.external_links ?? 0} found` },
        { label: 'H2 headings', importance: 'Important', status: tech.h2_count > 0 ? 'pass' : 'warn', value: `${tech.h2_count ?? 0} found` },
        { label: 'H3 headings', importance: 'Nice to have', status: 'info', value: `${tech.h3_count ?? 0} found` },
      ],
    },
    {
      title: 'Technical',
      checks: [
        { label: 'HTTPS', importance: 'Very important', status: tech.https_enabled ? 'pass' : 'fail', value: tech.https_enabled ? 'Secure' : 'Not secure' },
        { label: 'Mobile viewport', importance: 'Very important', status: tech.mobile_viewport ? 'pass' : 'fail', value: tech.mobile_viewport ? 'Set' : 'Missing' },
        { label: 'Language declaration', importance: 'Nice to have', status: tech.has_lang ? 'pass' : 'optional', value: tech.lang_attribute || (tech.has_lang ? 'Set' : 'Not set') },
      ],
    },
    {
      title: 'Social & schema',
      checks: [
        { label: 'Structured data (schema)', importance: 'Nice to have', status: tech.has_schema ? 'pass' : 'optional', value: tech.has_schema ? 'Found' : 'Not found' },
        { label: 'Open Graph title', importance: 'Nice to have', status: tech.has_og_title ? 'pass' : 'optional', value: tech.has_og_title ? 'Present' : 'Missing' },
        { label: 'Open Graph description', importance: 'Nice to have', status: tech.has_og_description ? 'pass' : 'optional', value: tech.has_og_description ? 'Present' : 'Missing' },
        { label: 'Open Graph image', importance: 'Nice to have', status: tech.has_og_image ? 'pass' : 'optional', value: tech.has_og_image ? 'Present' : 'Missing' },
        { label: 'Twitter Card', importance: 'Nice to have', status: tech.has_twitter_card ? 'pass' : 'optional', value: tech.has_twitter_card ? 'Present' : 'Missing' },
      ],
    },
  ]
}

function groupStats(group) {
  const counted = group.checks.filter(c => c.status !== 'info')
  const passed = counted.filter(c => c.status === 'pass').length
  const required = counted.filter(c => c.status !== 'optional')
  const reqPassed = required.filter(c => c.status === 'pass').length
  const color = required.length === 0
    ? '#8a8a8a'
    : reqPassed === required.length ? '#22c55e' : reqPassed / required.length >= 0.5 ? '#f97316' : '#ff6b75'
  return { passed, total: counted.length, color }
}

function CheckItem({ label, value, status, importance }) {
  const s = STATUS[status] || STATUS.info
  return (
    <li className="check-row" style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) auto', gap: '6px 16px', alignItems: 'center', padding: '11px 18px', borderBottom: '1px solid #181818' }}>
      <div style={{ minWidth: 0 }}>
        <span style={{ fontSize: '13px', color: '#d0d0d0' }}>{label}</span>
        {value != null && (
          <span style={{ fontSize: '12px', color: 'var(--text-body)', marginLeft: '8px', wordBreak: 'break-word' }}>{value}</span>
        )}
        {importance && (
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>{importance}</div>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'flex-end' }}>
        <span aria-hidden="true" style={{ display: 'inline-block', width: '8px', height: '8px', borderRadius: '50%', background: s.color, flexShrink: 0 }} />
        <span style={{ fontSize: '11px', color: s.color, fontWeight: 700, letterSpacing: '0.03em', whiteSpace: 'nowrap' }}>{s.label}</span>
      </div>
    </li>
  )
}

function CheckGroup({ group }) {
  const { passed, total, color } = groupStats(group)
  return (
    <div style={{ background: '#111', border: '1px solid #222', borderRadius: '10px', overflow: 'hidden', marginBottom: '12px' }}>
      <div style={{ background: '#161616', padding: '13px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', borderBottom: '1px solid #222', flexWrap: 'wrap' }}>
        <h3 style={{ fontSize: '13px', fontWeight: 700, color: '#fff', margin: 0 }}>{group.title}</h3>
        <span style={{ fontSize: '12px', color, fontWeight: 700 }}>{passed} of {total} checks passed</span>
      </div>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {group.checks.map(c => <CheckItem key={c.label} {...c} />)}
      </ul>
    </div>
  )
}

const sectionH2 = { fontSize: '16px', fontWeight: 800, color: '#fff', margin: '0 0 14px' }
const smallBtn = {
  background: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: '8px', padding: '8px 12px',
  color: '#e0e0e0', fontSize: '12px', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
}

export default function ResultsReport({ data, headingRef, onRescan, onNewScan, onCopyLink, copied, rescanning }) {
  const tech = data.technical_seo || {}
  const recs = sortRecs(data.recommendations)

  const [showAllTasks, setShowAllTasks] = useState(false)
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
      setLocalError(err?.message || 'Local SEO check failed. Please try again.')
    } finally {
      setLocalLoading(false)
    }
  }

  const groups = buildChecks(data)
  const mainScore = Number(data.seo_score) || 0
  const band = scoreBand(mainScore)
  const scoreAngle = mainScore * 3.6
  const shownRecs = showAllTasks ? recs : recs.slice(0, TASKS_PREVIEW)
  const titleOk = hasTitle(data)
  const metaOk = hasMeta(data)

  return (
    <div style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* ── Header ── */}
      <div style={{ background: '#161616', border: '1px solid #2a2a2a', borderRadius: '10px', padding: '14px 18px', display: 'flex', flexWrap: 'wrap', gap: '12px 24px', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ minWidth: 0, flex: '1 1 260px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.06em', marginBottom: '2px' }}>PAGE</div>
          <div style={{ fontSize: '13px', color: '#fff', fontWeight: 600, wordBreak: 'break-all' }}>{data.url}</div>
          {data.keyword && (
            <div style={{ fontSize: '12px', color: 'var(--text-body)', marginTop: '4px' }}>
              Keyword: <span style={{ color: '#ff6b75', fontWeight: 600 }}>"{data.keyword}"</span>
            </div>
          )}
          {data.cached === true && (
            <div style={{ fontSize: '12px', color: 'var(--text-body)', marginTop: '6px' }}>
              {data.cached_at ? `Result from ${relativeTime(data.cached_at)}` : 'Saved result'}
              {' · '}
              <button
                type="button"
                className="no-print"
                onClick={onRescan}
                disabled={rescanning}
                style={{ background: 'none', border: 'none', color: '#ff8a92', fontWeight: 700, textDecoration: 'underline', cursor: 'pointer', padding: 0, fontSize: '12px', fontFamily: 'inherit' }}
              >
                Re-scan
              </button>
            </div>
          )}
        </div>
        <div className="no-print btn-row" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button type="button" style={smallBtn} onClick={onNewScan}>New scan</button>
          <button type="button" style={smallBtn} onClick={onCopyLink}>{copied ? '✓ Link copied' : 'Copy link'}</button>
          <button type="button" style={smallBtn} onClick={() => window.print()}>Save as PDF</button>
        </div>
      </div>

      {/* ── Indexability ── */}
      <IndexabilityBanner indexability={data.indexability} uncapped={data.seo_score_uncapped} />

      {/* ── Score + verdict + breakdown ── */}
      <section aria-labelledby="score-h" style={{ background: '#111', border: '1px solid #222', borderRadius: '12px', padding: '24px' }}>
        <h2 id="score-h" ref={headingRef} tabIndex={-1} style={sectionH2}>Your on-page score</h2>
        <div style={{ display: 'flex', gap: '32px', flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px', flexShrink: 0, margin: '0 auto' }}>
            <div
              role="img"
              aria-label={`On-page score ${mainScore} of 100`}
              style={{
                width: '140px', height: '140px', borderRadius: '50%',
                background: `conic-gradient(${band.color} 0deg ${scoreAngle}deg, #1e1e1e ${scoreAngle}deg 360deg)`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: `0 0 0 2px #111, 0 0 24px ${band.color}22`,
              }}
            >
              <div style={{
                width: '104px', height: '104px', borderRadius: '50%', background: '#111',
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1px',
              }}>
                <span style={{ fontSize: '34px', fontWeight: 900, color: band.color, lineHeight: 1 }}>{mainScore}</span>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.08em', fontWeight: 700 }}>of 100</span>
              </div>
            </div>
            <div style={{ fontSize: '12px', color: band.color, fontWeight: 700 }}>{band.label}</div>
          </div>

          <div style={{ flex: '1 1 260px', minWidth: 0 }}>
            <p style={{ fontSize: '15px', color: '#e8e8e8', lineHeight: 1.55, margin: '0 0 18px' }}>
              {verdictFor(mainScore, data.keyword)}
            </p>
            <h3 style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.1em', margin: '0 0 10px' }}>CHECKS BY AREA</h3>
            <ul className="grid-auto" style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '8px 24px' }}>
              {groups.map(g => {
                const st = groupStats(g)
                return (
                  <li key={g.title} style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', fontSize: '12px' }}>
                    <span style={{ color: 'var(--text-body)' }}>{g.title}</span>
                    <span style={{ color: st.color, fontWeight: 700, whiteSpace: 'nowrap' }}>{st.passed} of {st.total} passed</span>
                  </li>
                )
              })}
            </ul>
          </div>
        </div>
      </section>

      {/* ── Your next 3 fixes ── */}
      <NextFixes recs={recs} />

      {/* ── Full task list ── */}
      {recs.length > 0 && (
        <section aria-labelledby="tasks-h" style={{ background: '#111', border: '1px solid #222', borderRadius: '12px', overflow: 'hidden' }}>
          <div style={{ background: '#161616', padding: '14px 20px', borderBottom: '1px solid #222', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 id="tasks-h" style={{ ...sectionH2, margin: 0, fontSize: '14px' }}>All tasks, by priority</h2>
            <span style={{
              fontSize: '11px', fontWeight: 700, color: 'var(--text-body)', background: '#1e1e1e',
              border: '1px solid #2a2a2a', padding: '1px 8px', borderRadius: '99px',
            }}>{recs.length}</span>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="tasks-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#0e0e0e' }}>
                  {['Priority', 'Task', 'Why it matters'].map(h => (
                    <th key={h} scope="col" style={{ padding: '9px 16px', fontSize: '10px', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.08em', textAlign: 'left', borderBottom: '1px solid #1e1e1e', textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {shownRecs.map((rec, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #181818' }}>
                    <td data-label="Priority" style={{ padding: '12px 16px', whiteSpace: 'nowrap', width: '110px', verticalAlign: 'top' }}>
                      <PriorityBadge priority={rec.priority} />
                    </td>
                    <td data-label="Task" style={{ padding: '12px 16px', verticalAlign: 'top' }}>
                      <div style={{ fontSize: '13px', color: '#e8e8e8', fontWeight: 600, marginBottom: '3px' }}>{rec.issue}</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-body)' }}>{rec.fix}</div>
                    </td>
                    <td data-label="Why it matters" style={{ padding: '12px 16px', fontSize: '12px', color: 'var(--text-body)', minWidth: '160px', verticalAlign: 'top' }}>{whyText(rec.impact)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {recs.length > TASKS_PREVIEW && (
            <div style={{ padding: '12px 20px', borderTop: '1px solid #1e1e1e' }} className="no-print">
              <button type="button" style={smallBtn} aria-expanded={showAllTasks} onClick={() => setShowAllTasks(v => !v)}>
                {showAllTasks ? 'Show fewer' : `Show all ${recs.length}`}
              </button>
            </div>
          )}
        </section>
      )}

      {/* ── Detailed checks ── */}
      <details className="details-block" style={{ background: '#0f0f0f', border: '1px solid #222', borderRadius: '12px', padding: '0' }}>
        <summary style={{ padding: '16px 20px', cursor: 'pointer', fontSize: '14px', fontWeight: 800, color: '#fff' }}>
          <h2 style={{ display: 'inline', fontSize: '14px', margin: 0 }}>Detailed checks and page info</h2>
        </summary>
        <div style={{ padding: '0 16px 16px' }}>
          <div style={{ background: '#111', border: '1px solid #222', borderRadius: '10px', padding: '18px', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 700, letterSpacing: '0.1em', margin: '0 0 14px' }}>PAGE INFORMATION</h3>
            <dl style={{ display: 'flex', flexDirection: 'column', gap: '10px', margin: '0 0 16px' }}>
              {[
                { label: 'Page title', value: titleOk ? data.title : 'Missing', bad: !titleOk },
                { label: 'Meta description', value: metaOk ? data.meta_description : 'Missing', bad: !metaOk },
                { label: 'Page URL', value: data.final_url || data.url || '—', bad: false },
              ].map(row => (
                <div key={row.label} className="info-row" style={{ display: 'grid', gridTemplateColumns: 'minmax(0,130px) minmax(0,1fr)', gap: '12px', alignItems: 'flex-start' }}>
                  <dt style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600, paddingTop: '1px' }}>{row.label}</dt>
                  <dd style={{ margin: 0, fontSize: '13px', color: row.bad ? '#ff6b75' : '#d0d0d0', wordBreak: 'break-word', lineHeight: 1.5 }}>{row.value}</dd>
                </div>
              ))}
            </dl>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {[
                { label: 'Words', val: Number(data.word_count ?? 0).toLocaleString() },
                { label: 'Language', val: tech.lang_attribute || '—' },
                { label: 'H1 tags', val: tech.h1_count ?? '—' },
                { label: 'HTTP status', val: data.http_status ?? '—' },
              ].map(chip => (
                <div key={chip.label} style={{ background: '#161616', border: '1px solid #2a2a2a', borderRadius: '8px', padding: '8px 14px', textAlign: 'center', minWidth: '64px' }}>
                  <div style={{ fontSize: '10px', color: 'var(--text-muted)', letterSpacing: '0.06em', marginBottom: '3px', fontWeight: 600 }}>{chip.label}</div>
                  <div style={{ fontSize: '13px', fontWeight: 800, color: '#d0d0d0' }}>{String(chip.val)}</div>
                </div>
              ))}
            </div>
          </div>
          {groups.map(g => <CheckGroup key={g.title} group={g} />)}
        </div>
      </details>

      {/* ── Tools ── */}
      <section aria-labelledby="tools-h" className="no-print">
        <h2 id="tools-h" style={sectionH2}>Fix-it tools</h2>
        <div className="grid-auto" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
          <MetaSuggestPanel url={data.url} keyword={data.keyword} />
          <SchemaPanel url={data.url} keyword={data.keyword} />
        </div>

        <div style={{ marginTop: '12px' }}>
          {!localData && (
            <button
              type="button"
              onClick={handleCheckLocalSeo}
              disabled={localLoading}
              style={{
                width: '100%', padding: '12px 20px',
                background: localLoading ? '#1a1a1a' : '#161616',
                border: '1px solid #2a2a2a', borderRadius: '10px',
                color: localLoading ? 'var(--text-muted)' : 'var(--text-body)',
                fontSize: '13px', fontWeight: 600,
                cursor: localLoading ? 'default' : 'pointer', letterSpacing: '0.02em',
                transition: 'background 0.15s, color 0.15s',
              }}
            >
              {localLoading ? 'Checking local SEO signals…' : '📍 Check Local SEO'}
            </button>
          )}
          {localError && (
            <div role="alert" style={{ fontSize: '12px', color: '#ff6b75', marginTop: '8px', textAlign: 'center' }}>{localError}</div>
          )}
          {localData && <LocalSeoPanel data={localData} />}
          {localData && localData.local_score >= 80 && !localData.local_checks?.some(c => !c.pass) && (
            <div style={{ background: '#111', border: '1px solid #222', borderRadius: '10px', padding: '14px 20px', display: 'flex', gap: '10px', alignItems: 'center' }}>
              <span style={{ color: '#22c55e', fontSize: '16px' }}>✓</span>
              <span style={{ fontSize: '13px', color: '#22c55e', fontWeight: 600 }}>Local SEO looks great: score {localData.local_score}/100, all checks passing.</span>
            </div>
          )}
        </div>
      </section>

      {/* ── GEO, then deep crawl ── */}
      {data.geo_score && <GeoScorePanel geo={data.geo_score} />}
      {data.deep_crawl && <DeepCrawlPanel data={data.deep_crawl} />}

      {/* ── Rank tracker ── */}
      <div className="no-print">
        <RankTracker url={data.url} keyword={data.keyword} />
      </div>
    </div>
  )
}
