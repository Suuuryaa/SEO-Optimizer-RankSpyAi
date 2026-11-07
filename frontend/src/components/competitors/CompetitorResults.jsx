import { scoreBand } from '../../lib/score'

const BLOCKED_COPY = "Couldn't scan this site, it blocked our crawler."

// Google position: int → "#n", null → "Not in top 30", "unknown"/missing → "Unknown"
function positionInfo(pos) {
  if (typeof pos === 'number' && Number.isFinite(pos)) return { label: `#${pos}`, sort: pos }
  if (pos === null) return { label: 'Not in top 30', sort: 1000 }
  return { label: 'Unknown', sort: 2000 }
}

function rowPosition(c, key) {
  return Object.prototype.hasOwnProperty.call(c, key) ? c[key] : undefined
}

function hostOf(url) {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url || '' }
}

function kwFlag(flag, match) {
  if (match === 'all_tokens') return 'partly'
  if (match === 'exact') return 'yes'
  if (flag === true || flag === '✓') return 'yes'
  if (flag === false || flag === '✗') return 'no'
  return 'unknown'
}

function normalizePrimary(p) {
  if (!p) return null
  return {
    you: true,
    url: p.url ?? '',
    title: p.title || p.url || '',
    score: Number(p.seo_score ?? 0),
    words: p.word_count ?? null,
    kwTitle: kwFlag(p.keyword_in_title, p.keyword_match?.title),
    kwH1: kwFlag(p.keyword_in_h1, p.keyword_match?.h1),
    pos: positionInfo(rowPosition(p, 'google_position')),
    error: null,
  }
}

function normalizeComp(c) {
  const url = c.url ?? c.URL ?? ''
  const blocked = !!c.error || c['Score Band'] === 'Blocked'
  return {
    you: false,
    url,
    title: c.title ?? c['Venue Name'] ?? url,
    score: Number(c.seo_score ?? c['SEO Score'] ?? 0),
    words: c.word_count ?? c['Word Count'] ?? null,
    kwTitle: kwFlag(c.keyword_in_title ?? c['Keyword in Title'], c.keyword_match?.title),
    kwH1: kwFlag(c.keyword_in_h1 ?? c['Keyword in H1'], c.keyword_match?.h1),
    pos: positionInfo('SERP Rank' in c ? c['SERP Rank'] : c.google_position),
    // New backends send user-safe text with error_kind; older ones sent raw exception text.
    error: blocked ? ((c.error_kind && c.error) ? String(c.error) : BLOCKED_COPY) : null,
  }
}

function KwCell({ v }) {
  if (v === 'yes') return <span style={{ color: '#22c55e', fontWeight: 700 }}>Yes</span>
  if (v === 'partly') return <span style={{ color: '#f97316', fontWeight: 700 }}>Partly</span>
  if (v === 'no') return <span style={{ color: '#ff6b75', fontWeight: 700 }}>No</span>
  return <span style={{ color: 'var(--text-muted)' }}>—</span>
}

function ScoreCell({ row }) {
  if (row.error) return <span style={{ color: 'var(--text-muted)' }}>—</span>
  const b = scoreBand(row.score)
  return <span style={{ color: b.color, fontWeight: 800 }}>{row.score}</span>
}

function SiteCell({ row }) {
  return (
    <div style={{ minWidth: 0 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
        {row.you && (
          <span style={{ fontSize: '10px', fontWeight: 800, color: '#fff', background: '#e63946', borderRadius: '4px', padding: '2px 6px', flexShrink: 0 }}>
            You
          </span>
        )}
        <span style={{ fontSize: '13px', color: '#fff', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {hostOf(row.url) || row.title}
        </span>
      </div>
      {row.error && (
        <div style={{ fontSize: '12px', color: '#f0a0a6', marginTop: '3px' }}>{row.error}</div>
      )}
    </div>
  )
}

const th = { padding: '9px 12px', fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', textAlign: 'left', borderBottom: '1px solid #222', whiteSpace: 'nowrap' }
const td = { padding: '11px 12px', fontSize: '13px', color: '#d0d0d0', borderBottom: '1px solid #1a1a1a', verticalAlign: 'top' }

function RowCard({ row }) {
  return (
    <li style={{
      background: row.you ? 'rgba(230,57,70,0.07)' : '#111',
      border: `1px solid ${row.you ? 'rgba(230,57,70,0.4)' : '#222'}`,
      borderRadius: '10px', padding: '14px',
    }}>
      <SiteCell row={row} />
      <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0,1fr))', gap: '8px 12px', margin: '10px 0 0', fontSize: '12px' }}>
        {[
          ['Google position', <span key="p">{row.pos.label}</span>],
          ['On-page score', <ScoreCell key="s" row={row} />],
          ['Words', row.error ? '—' : (row.words != null ? Number(row.words).toLocaleString() : '—')],
          ['Keyword in title', row.error ? '—' : <KwCell key="t" v={row.kwTitle} />],
          ['Keyword in H1', row.error ? '—' : <KwCell key="h" v={row.kwH1} />],
        ].map(([k, v]) => (
          <div key={k} style={{ minWidth: 0 }}>
            <dt style={{ color: 'var(--text-muted)', fontSize: '11px' }}>{k}</dt>
            <dd style={{ margin: 0, color: '#e0e0e0' }}>{v}</dd>
          </div>
        ))}
      </dl>
    </li>
  )
}

export default function CompetitorResults({ data }) {
  const raw = Array.isArray(data) ? data : (data?.competitors ?? data?.results ?? [])
  const competitors = raw.map(normalizeComp)
  const primary = Array.isArray(data) ? null : normalizePrimary(data?.primary)
  const locationLabel = data?.search_location?.label

  if (competitors.length === 0 && !primary) {
    return (
      <div style={{ background: '#161616', border: '1px solid #2a2a2a', borderRadius: '12px', padding: '40px 16px', textAlign: 'center', color: 'var(--text-body)', marginTop: '24px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 700, color: '#fff', margin: '0 0 8px' }}>No competitors found</h2>
        <p style={{ fontSize: '13px' }}>Try a different URL or keyword to find competitor data.</p>
      </div>
    )
  }

  // Order by real Google position; sites we couldn't scan go last.
  const sorted = [...competitors].sort((a, b) =>
    (a.error ? 1 : 0) - (b.error ? 1 : 0) || a.pos.sort - b.pos.sort || b.score - a.score)
  const rows = primary ? [primary, ...sorted] : sorted

  return (
    <section aria-labelledby="vs-h" style={{ marginTop: '16px', background: '#161616', border: '1px solid #2a2a2a', borderRadius: '12px', padding: '18px 16px' }}>
      <h2 id="vs-h" style={{ fontSize: '16px', fontWeight: 800, color: '#fff', margin: '0 0 4px' }}>You vs competitors</h2>
      <p style={{ fontSize: '12px', color: 'var(--text-body)', margin: '0 0 14px' }}>
        {locationLabel ? `Searched Google in: ${locationLabel}` : (data?.location_msg || '')}
        {(locationLabel || data?.location_msg) ? ' · ' : ''}
        On-page score is our estimate from each page's HTML; Google position is the real search result.
      </p>

      {competitors.length === 0 && (
        <p style={{ fontSize: '13px', color: 'var(--text-body)', margin: '0 0 12px' }}>
          We couldn't find competitors for this keyword. Try a more specific keyword.
        </p>
      )}

      <div className="comp-table" style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <caption className="sr-only">Your page compared with competitor pages</caption>
          <thead>
            <tr>
              <th scope="col" style={th}>Site</th>
              <th scope="col" style={th}>Google position</th>
              <th scope="col" style={th}>On-page score</th>
              <th scope="col" style={th}>Words</th>
              <th scope="col" style={th}>Keyword in title</th>
              <th scope="col" style={th}>Keyword in H1</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={`${row.url}-${i}`} style={row.you ? { background: 'rgba(230,57,70,0.08)', boxShadow: 'inset 3px 0 0 #e63946' } : undefined}>
                <td style={{ ...td, maxWidth: '260px' }}><SiteCell row={row} /></td>
                <td style={{ ...td, whiteSpace: 'nowrap' }}>{row.pos.label}</td>
                <td style={td}><ScoreCell row={row} /></td>
                <td style={td}>{row.error ? '—' : (row.words != null ? Number(row.words).toLocaleString() : '—')}</td>
                <td style={td}>{row.error ? '—' : <KwCell v={row.kwTitle} />}</td>
                <td style={td}>{row.error ? '—' : <KwCell v={row.kwH1} />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="comp-cards" style={{ listStyle: 'none', margin: 0, padding: 0, flexDirection: 'column', gap: '10px' }}>
        {rows.map((row, i) => <RowCard key={`${row.url}-${i}`} row={row} />)}
      </ul>
    </section>
  )
}
