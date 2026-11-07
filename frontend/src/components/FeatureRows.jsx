// Zig-zag feature rows (the Semrush / SEOptimer pattern): a short pitch and a
// button on one side, a slice of the real report UI on the other.
// All panel data is example data and is labelled as such.

const panel = {
  background: '#121212', border: '1px solid #262626', borderRadius: '16px', padding: '22px',
  boxShadow: '0 20px 60px rgba(0,0,0,0.45)',
}
const eyebrow = { fontSize: '12px', fontWeight: 700, letterSpacing: '0.08em', color: '#e63946', textTransform: 'uppercase', marginBottom: '12px' }
const small = { fontSize: '11px', fontWeight: 700, letterSpacing: '0.08em', color: 'var(--text-muted, #8a8a8a)', textTransform: 'uppercase' }
const tone = (s) => (s >= 70 ? '#22c55e' : s >= 40 ? '#f97316' : '#e63946')

function goToScan() {
  document.getElementById('scan')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  setTimeout(() => document.getElementById('url-input')?.focus({ preventScroll: true }), 400)
}

function Row({ eyebrowText, title, text, bullets, cta, flip, children }) {
  return (
    <div className={`feature-row${flip ? ' flip' : ''}`}>
      <div className="feature-copy">
        <div style={eyebrow}>{eyebrowText}</div>
        <h3 style={{ fontSize: 'clamp(24px, 2.8vw, 32px)', fontWeight: 800, letterSpacing: '-0.02em', lineHeight: 1.15, color: '#fff', margin: '0 0 14px' }}>
          {title}
        </h3>
        <p style={{ fontSize: '16px', color: 'var(--text-body, #a0a0a0)', lineHeight: 1.6, margin: '0 0 16px' }}>{text}</p>
        <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 22px', display: 'grid', gap: '8px' }}>
          {bullets.map((b) => (
            <li key={b} style={{ fontSize: '14px', color: '#cfcfcf', display: 'flex', gap: '8px' }}>
              <span aria-hidden="true" style={{ color: '#22c55e' }}>✓</span>{b}
            </li>
          ))}
        </ul>
        <button
          type="button"
          onClick={goToScan}
          style={{ background: '#e63946', color: '#fff', border: 'none', borderRadius: '8px', padding: '12px 20px', fontWeight: 700, fontSize: '14px', cursor: 'pointer' }}
        >
          {cta}
        </button>
      </div>
      <div className="feature-visual" aria-label="Example from a RankSpy report">{children}</div>
    </div>
  )
}

function FixesPanel() {
  const fixes = [
    ['Add “emergency plumber” to your page title', 'Titles are the strongest on-page relevance signal.', 'Fix first'],
    ['Put the keyword in your main H1 heading', 'Your H1 says “Welcome”, which tells Google nothing.', 'Fix first'],
    ['Add alt text to 6 images', 'Helps image search and screen-reader users.', 'Fix next'],
  ]
  return (
    <div style={panel}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', paddingBottom: '16px', borderBottom: '1px solid #222' }}>
        <div aria-hidden="true" style={{ width: '64px', height: '64px', borderRadius: '50%', flex: 'none', background: 'conic-gradient(#f97316 0 58%, #262626 58% 100%)', display: 'grid', placeItems: 'center' }}>
          <div style={{ width: '50px', height: '50px', borderRadius: '50%', background: '#121212', display: 'grid', placeItems: 'center', fontWeight: 800, color: '#f97316', fontSize: '19px' }}>58</div>
        </div>
        <div>
          <div style={{ fontWeight: 700, color: '#f97316' }}>Needs work</div>
          <div style={{ fontSize: '13px', color: 'var(--text-body, #a0a0a0)' }}>Good base. These fixes help this page compete.</div>
        </div>
      </div>
      <div style={{ ...small, margin: '16px 0 10px' }}>Your next 3 fixes</div>
      <ol style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '10px' }}>
        {fixes.map(([fix, why, badge], i) => (
          <li key={fix} style={{ display: 'flex', gap: '12px', background: '#171717', border: '1px solid #232323', borderRadius: '10px', padding: '10px 12px' }}>
            <span style={{ flex: 'none', width: '22px', height: '22px', borderRadius: '50%', background: 'rgba(230,57,70,0.15)', color: '#ff8a93', fontSize: '12px', fontWeight: 700, display: 'grid', placeItems: 'center' }}>{i + 1}</span>
            <span style={{ flex: 1, minWidth: 0 }}>
              <span style={{ display: 'block', color: '#fff', fontSize: '14px', fontWeight: 600 }}>{fix}</span>
              <span style={{ display: 'block', color: 'var(--text-muted, #8a8a8a)', fontSize: '12.5px', marginTop: '2px' }}>{why}</span>
            </span>
            <span style={{ flex: 'none', alignSelf: 'flex-start', fontSize: '11px', fontWeight: 700, color: badge === 'Fix first' ? '#ff8a93' : '#f5b041', border: `1px solid ${badge === 'Fix first' ? 'rgba(230,57,70,0.4)' : 'rgba(245,176,65,0.4)'}`, borderRadius: '5px', padding: '2px 7px' }}>{badge}</span>
          </li>
        ))}
      </ol>
    </div>
  )
}

function CompetitorPanel() {
  const rows = [
    ['yourplumbing.co.nz', '#14', 58, true],
    ['cityplumbers.co.nz', '#2', 81, false],
    ['fixitfast.nz', '#5', 74, false],
    ['aceplumbing.co.nz', 'Not in top 30', 49, false],
  ]
  return (
    <div style={panel}>
      <div style={{ ...small, marginBottom: '4px' }}>You vs. competitors</div>
      <div style={{ fontSize: '13px', color: 'var(--text-body, #a0a0a0)', marginBottom: '12px' }}>“emergency plumber auckland” · Google New Zealand</div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px', minWidth: '360px' }}>
          <thead>
            <tr style={{ color: 'var(--text-muted, #8a8a8a)', textAlign: 'left' }}>
              <th style={{ padding: '8px 6px', fontWeight: 600 }}>Site</th>
              <th style={{ padding: '8px 6px', fontWeight: 600 }}>Google</th>
              <th style={{ padding: '8px 6px', fontWeight: 600 }}>On-page</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([site, pos, score, you]) => (
              <tr key={site} style={{ borderTop: '1px solid #222', background: you ? 'rgba(230,57,70,0.07)' : 'transparent' }}>
                <td style={{ padding: '10px 6px', color: '#fff' }}>
                  {you && <span style={{ fontSize: '10px', fontWeight: 700, color: '#ff8a93', border: '1px solid rgba(230,57,70,0.4)', borderRadius: '4px', padding: '1px 5px', marginRight: '8px' }}>YOU</span>}
                  {site}
                </td>
                <td style={{ padding: '10px 6px', color: '#cfcfcf' }}>{pos}</td>
                <td style={{ padding: '10px 6px' }}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                    <span aria-hidden="true" style={{ width: '60px', height: '6px', background: '#262626', borderRadius: '3px', overflow: 'hidden' }}>
                      <span style={{ display: 'block', width: `${score}%`, height: '100%', background: tone(score) }} />
                    </span>
                    <span style={{ color: tone(score), fontWeight: 700 }}>{score}</span>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: '14px', fontSize: '13px', color: '#cfcfcf', background: '#171717', border: '1px solid #232323', borderRadius: '10px', padding: '10px 12px' }}>
        <span style={{ color: '#ff8a93', fontWeight: 700 }}>AI insight · </span>
        Both top rivals show their phone number and service area in the H1. You don&rsquo;t.
      </div>
    </div>
  )
}

function AiPanel() {
  const bots = [
    ['ChatGPT search (OAI-SearchBot)', 'Allowed', '#22c55e'],
    ['Perplexity (PerplexityBot)', 'Allowed', '#22c55e'],
    ['Claude search (Claude-SearchBot)', 'Blocked', '#e63946'],
    ['GPTBot (AI training)', 'Your choice', 'var(--text-muted, #8a8a8a)'],
  ]
  return (
    <div style={panel}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '14px' }}>
        <div style={small}>AI visibility</div>
        <div><span style={{ fontSize: '26px', fontWeight: 800, color: '#f97316' }}>64</span><span style={{ color: 'var(--text-muted, #8a8a8a)', fontSize: '13px' }}> / 100</span></div>
      </div>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'grid', gap: '8px' }}>
        {bots.map(([name, status, c]) => (
          <li key={name} style={{ display: 'flex', justifyContent: 'space-between', gap: '10px', fontSize: '13px', background: '#171717', border: '1px solid #232323', borderRadius: '10px', padding: '9px 12px' }}>
            <span style={{ color: '#e6e6e6' }}>{name}</span>
            <span style={{ color: c, fontWeight: 700, whiteSpace: 'nowrap' }}>{status}</span>
          </li>
        ))}
      </ul>
      <div style={{ marginTop: '12px', fontSize: '13px', color: '#cfcfcf' }}>
        <span style={{ color: '#f5b041', fontWeight: 700 }}>Fix: </span>your robots.txt blocks Claude-SearchBot, so Claude can&rsquo;t cite this page.
      </div>
    </div>
  )
}

export default function FeatureRows() {
  return (
    <div className="feature-rows" style={{ padding: '64px 0 24px', display: 'grid', gap: '88px' }}>
      <Row
        eyebrowText="On-page audit"
        title="A to-do list, not a wall of data"
        text="Every scan ends with the three changes that will help most, in plain English, with why each one matters."
        bullets={['30+ on-page checks in about a minute', 'Fixes ranked: Fix first, Fix next, Nice to have', 'Flags pages Google can’t index before anything else']}
        cta="Analyze my page"
      >
        <FixesPanel />
      </Row>
      <Row
        flip
        eyebrowText="Competitor comparison"
        title="See who’s beating you on Google, and why"
        text="We find the sites ranking for your keyword, check their real Google positions in your country and compare them with your page."
        bullets={['Real positions from Google, not estimates', 'Side-by-side on-page scores', 'An AI-written strategy for closing the gap']}
        cta="Find my competitors"
      >
        <CompetitorPanel />
      </Row>
      <Row
        eyebrowText="AI visibility"
        title="Know if ChatGPT and Perplexity can see you"
        text="AI answers are the new search results. We check whether AI search tools are allowed to read your page and how quotable it is."
        bullets={['AI search bots vs. AI training bots, kept separate', 'Snippet controls and llms.txt checked', 'Clear fixes when something blocks AI search']}
        cta="Check my AI visibility"
      >
        <AiPanel />
      </Row>
      <p style={{ textAlign: 'center', fontSize: '12px', color: 'var(--text-muted, #8a8a8a)', margin: '-56px 0 0' }}>
        Panels show example data for a local plumber.
      </p>
    </div>
  )
}
