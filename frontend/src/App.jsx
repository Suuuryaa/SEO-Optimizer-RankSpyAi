import { useEffect, useRef, useState } from 'react'
import './index.css'
import { analyzeUrl, findCompetitors, AI_REPORT_UNAVAILABLE } from './api'
import Navbar from './components/Navbar'
import ContactModal from './components/ContactModal'
import Hero from './components/Hero'
import InputForm from './components/InputForm'
import ResultsReport from './components/results/ResultsReport'
import CompetitorResults from './components/competitors/CompetitorResults'
import HowItWorks from './components/HowItWorks'
import FeatureRows from './components/FeatureRows'
import ScoreScale from './components/ScoreScale'
import FAQSection from './components/FAQSection'
import Footer from './components/Footer'
import LegalModal from './components/LegalModal'
import ContentBriefPanel from './components/results/ContentBriefPanel'

// ?url=&keyword=&mode=analyze|competitors — prefills the form, never auto-runs.
function readShareParams() {
  try {
    const q = new URLSearchParams(window.location.search)
    const url = (q.get('url') || '').slice(0, 2000)
    if (!url) return null
    const mode = q.get('mode') === 'competitors' ? 'competitors' : 'analyze'
    return { url, keyword: (q.get('keyword') || '').slice(0, 200), mode }
  } catch {
    return null
  }
}

function writeShareParams({ url, keyword, mode }) {
  try {
    const q = new URLSearchParams()
    q.set('url', url)
    if (keyword) q.set('keyword', keyword)
    q.set('mode', mode)
    window.history.replaceState(null, '', `${window.location.pathname}?${q.toString()}`)
  } catch { /* ignore */ }
}

function LoadingOverlay({ progress, onCancel }) {
  const steps = progress?.steps || []
  return (
    <div
      role="status"
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        padding: '56px 16px', gap: '16px', textAlign: 'center',
      }}
    >
      <div className="spinner" aria-hidden="true" />
      <div style={{ fontSize: '14px', color: '#d0d0d0', letterSpacing: '0.04em' }}>
        {progress?.step ? `${progress.step}…` : 'Starting your scan…'}
      </div>
      <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Usually 20–60 seconds</div>
      {steps.length > 1 && (
        <ol style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px', color: 'var(--text-muted)' }}>
          {steps.slice(0, -1).map((s, i) => (
            <li key={i}><span style={{ color: '#22c55e' }} aria-hidden="true">✓</span> {s}</li>
          ))}
        </ol>
      )}
      {progress?.elapsed > 0 && (
        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{Math.round(progress.elapsed)} s elapsed</div>
      )}
      <button
        type="button"
        onClick={onCancel}
        style={{
          background: 'transparent', border: '1px solid #3a3a3a', borderRadius: '8px', padding: '8px 18px',
          color: '#e0e0e0', fontSize: '12px', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
        }}
      >
        Cancel
      </button>
    </div>
  )
}

function ErrorBanner({ error, onAddKeys }) {
  return (
    <div
      role="alert"
      style={{
        background: 'rgba(230,57,70,0.08)',
        border: '1px solid rgba(230,57,70,0.35)',
        borderRadius: '10px',
        padding: '16px 20px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        maxWidth: '700px',
        margin: '24px auto 0',
      }}
    >
      <span style={{ fontSize: '18px' }} aria-hidden="true">⚠️</span>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: '14px', color: '#f0f0f0', lineHeight: 1.5 }}>{error.message}</div>
        {(error.kind === 'rate_limited' || error.kind === 'daily_limit') && (
          <button
            type="button"
            onClick={onAddKeys}
            style={{
              marginTop: '10px', background: '#e63946', color: '#fff', border: 'none', borderRadius: '8px',
              padding: '8px 14px', fontSize: '12px', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
            }}
          >
            Add your own free keys
          </button>
        )}
      </div>
    </div>
  )
}

// Minimal markdown renderer for the Gemini report: ## headings, - bullets, **bold**.
// React escapes all text, so model output can never inject HTML.
function renderInline(text) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={i} style={{ color: '#e8e8e8' }}>{part.slice(2, -2)}</strong>
      : part
  )
}

function AiReport({ text, error }) {
  // Old backends put the exception text in ai_summary; never show it.
  const unavailable = !!error || (typeof text === 'string' && /^AI summary (unavailable|error)/i.test(text))
  if (!text && !unavailable) return null
  return (
    <section
      aria-labelledby="ai-report-h"
      style={{
        background: 'rgba(230,57,70,0.05)',
        border: '1px solid rgba(230,57,70,0.2)',
        borderRadius: '12px',
        padding: '20px',
        marginTop: '24px',
      }}
    >
      <h2 id="ai-report-h" style={{ fontSize: '12px', color: '#ff6b75', fontWeight: 700, letterSpacing: '0.08em', margin: '0 0 12px' }}>
        AI STRATEGY REPORT
      </h2>
      {unavailable ? (
        <p style={{ fontSize: '13px', color: 'var(--text-body)' }}>{AI_REPORT_UNAVAILABLE}</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {text.split('\n').map((raw, i) => {
            const line = raw.trim()
            if (!line) return null
            const h = line.match(/^#{1,4}\s+(.*)/)
            if (h) return (
              <h3 key={i} style={{ fontSize: '14px', fontWeight: 700, color: '#fff', margin: i ? '12px 0 0' : 0 }}>
                {renderInline(h[1])}
              </h3>
            )
            const b = line.match(/^(?:[-*•]|\d+[.)])\s+(.*)/)
            if (b) return (
              <div key={i} style={{ fontSize: '13px', color: 'var(--text-body)', lineHeight: '1.6', paddingLeft: '14px', position: 'relative' }}>
                <span style={{ position: 'absolute', left: 0, color: '#e63946' }} aria-hidden="true">•</span>
                {renderInline(b[1])}
              </div>
            )
            return <p key={i} style={{ fontSize: '13px', color: 'var(--text-body)', lineHeight: '1.6' }}>{renderInline(line)}</p>
          })}
        </div>
      )}
    </section>
  )
}

const actionBtn = {
  background: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: '8px', padding: '8px 12px',
  color: '#e0e0e0', fontSize: '12px', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
}

export default function App() {
  const [initialShare] = useState(readShareParams)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)       // { kind, message }
  const [seoData, setSeoData] = useState(null)
  const [compData, setCompData] = useState(null)
  const [legalPage, setLegalPage] = useState(null)
  const [showContact, setShowContact] = useState(false)
  const [progress, setProgress] = useState(null)
  const [formTab, setFormTab] = useState('check')
  const [lastParams, setLastParams] = useState(null)
  const [liveMsg, setLiveMsg] = useState('')
  const [copied, setCopied] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  const abortRef = useRef(null)
  const scanIdRef = useRef(0)
  const urlRef = useRef(null)
  const resultsHeadingRef = useRef(null)
  const formWrapRef = useRef(null)

  // Move focus to the results heading once a scan finishes.
  useEffect(() => {
    if ((seoData || compData) && resultsHeadingRef.current) {
      resultsHeadingRef.current.focus({ preventScroll: true })
      resultsHeadingRef.current.scrollIntoView({ block: 'start', behavior: 'smooth' })
    }
  }, [seoData, compData])

  // "Save as PDF": expand collapsed sections so the printout has everything.
  useEffect(() => {
    const open = () => document.querySelectorAll('details').forEach(d => { d.dataset.wasOpen = d.open ? '1' : ''; d.open = true })
    const restore = () => document.querySelectorAll('details').forEach(d => { if (d.dataset.wasOpen === '') d.open = false })
    window.addEventListener('beforeprint', open)
    window.addEventListener('afterprint', restore)
    return () => {
      window.removeEventListener('beforeprint', open)
      window.removeEventListener('afterprint', restore)
    }
  }, [])

  async function runScan(kind, params) {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl
    const id = ++scanIdRef.current
    setLoading(true)
    setError(null)
    setSeoData(null)
    setCompData(null)
    setProgress(null)
    setLastParams({ kind, ...params })
    setLiveMsg('Scan started. This usually takes 20 to 60 seconds.')
    try {
      if (kind === 'analyze') {
        const result = await analyzeUrl({ ...params, onProgress: p => { if (id === scanIdRef.current) setProgress(p) }, signal: ctrl.signal })
        if (id !== scanIdRef.current) return
        setSeoData(result)
        const tasks = Array.isArray(result?.recommendations) ? result.recommendations.length : 0
        setLiveMsg(`Scan complete. Score ${result?.seo_score ?? 0} of 100. ${tasks} task${tasks === 1 ? '' : 's'}.`)
      } else {
        const result = await findCompetitors({ ...params, onProgress: p => { if (id === scanIdRef.current) setProgress(p) }, signal: ctrl.signal })
        if (id !== scanIdRef.current) return
        setCompData(result)
        const n = Array.isArray(result) ? result.length : (result?.competitors?.length ?? 0)
        setLiveMsg(`Competitor scan complete. ${n} competitor${n === 1 ? '' : 's'} compared.`)
      }
      writeShareParams({ url: params.url, keyword: params.keyword, mode: kind })
    } catch (err) {
      if (id !== scanIdRef.current) return
      if (err?.kind === 'cancelled') {
        setLiveMsg('Scan cancelled.')
      } else {
        const e = { kind: err?.kind || 'internal', message: err?.message || 'Something went wrong. Please try again.' }
        setError(e)
        setLiveMsg(e.message)
      }
    } finally {
      if (id === scanIdRef.current) {
        setLoading(false)
        setRefreshKey(k => k + 1)
      }
    }
  }

  function handleAnalyze({ url, keyword, crawlMode, geo, userApiKeys, fresh }) {
    runScan('analyze', { url, keyword, crawlMode, geo, userApiKeys, fresh })
  }

  function handleCompetitors({ url, keyword, userApiKeys }) {
    runScan('competitors', { url, keyword, userApiKeys })
  }

  function handleCancel() {
    abortRef.current?.abort()
    scanIdRef.current++
    setLoading(false)
    setProgress(null)
    setLiveMsg('Scan cancelled.')
    urlRef.current?.focus()
  }

  function handleRescan() {
    if (!lastParams || lastParams.kind !== 'analyze') return
    const { url, keyword, crawlMode, geo, userApiKeys } = lastParams
    handleAnalyze({ url, keyword, crawlMode, geo, userApiKeys, fresh: true })
  }

  function handleNewScan() {
    setSeoData(null)
    setCompData(null)
    setError(null)
    setFormTab('check')
    formWrapRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    setTimeout(() => urlRef.current?.focus({ preventScroll: true }), 0)
  }

  function handleAddKeys() {
    setFormTab('apikey')
    formWrapRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    setTimeout(() => document.getElementById('gemini-key')?.focus({ preventScroll: true }), 0)
  }

  function handleCopyLink() {
    const done = () => { setCopied(true); setTimeout(() => setCopied(false), 2000) }
    try {
      navigator.clipboard.writeText(window.location.href).then(done, () => {})
    } catch { /* clipboard unavailable */ }
  }

  const compCount = Array.isArray(compData) ? compData.length : (compData?.competitors?.length ?? 0)

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0a', paddingTop: '60px' }}>
      <a href="#main" className="skip-link">Skip to main content</a>
      <Navbar />

      {/* Beta banner */}
      <div className="no-print" style={{
        background: 'rgba(234,179,8,0.07)',
        borderBottom: '1px solid rgba(234,179,8,0.2)',
        padding: '9px 16px',
        textAlign: 'center',
        fontSize: '12px',
        color: '#c9b46a',
        letterSpacing: '0.02em',
      }}>
        <span style={{ fontWeight: 700, color: '#eab308' }}>Beta:</span>
        {' '}free while we build it. Scores are estimates based on your page's HTML, not a guarantee of rankings.
      </div>

      <div aria-live="polite" aria-atomic="true" className="sr-only">{liveMsg}</div>

      <main id="main" tabIndex={-1}>
        <div id="top" />
        <Hero>
          <div id="scan" ref={formWrapRef}>
            <InputForm
              onAnalyze={handleAnalyze}
              onCompetitors={handleCompetitors}
              loading={loading}
              activeTab={formTab}
              onTabChange={setFormTab}
              urlRef={urlRef}
              initial={initialShare}
              refreshKey={refreshKey}
            />
          </div>
        </Hero>

        <div className="page-wrap" style={{ maxWidth: '960px', margin: '0 auto', padding: '0 16px' }}>
          {error && <ErrorBanner error={error} onAddKeys={handleAddKeys} />}

          {loading && <LoadingOverlay progress={progress} onCancel={handleCancel} />}

          {!loading && seoData && (
            <div className="fade-in results-area">
              <ResultsReport
                data={seoData}
                headingRef={resultsHeadingRef}
                onRescan={handleRescan}
                onNewScan={handleNewScan}
                onCopyLink={handleCopyLink}
                copied={copied}
                rescanning={loading}
              />
            </div>
          )}

          {!loading && compData && (
            <div className="fade-in results-area">
              <div
                style={{
                  display: 'flex', flexWrap: 'wrap', gap: '12px', justifyContent: 'space-between', alignItems: 'center',
                  background: '#161616', border: '1px solid #2a2a2a', borderRadius: '10px', padding: '14px 18px', marginTop: '24px',
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <h2
                    ref={resultsHeadingRef}
                    tabIndex={-1}
                    style={{ fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.06em', margin: '0 0 2px', fontWeight: 700 }}
                  >
                    COMPETITOR ANALYSIS
                  </h2>
                  <div style={{ fontSize: '13px', color: '#fff', fontWeight: 600 }}>
                    {compCount} competitor{compCount === 1 ? '' : 's'} found
                    {lastParams?.keyword ? <> for <span style={{ color: '#ff6b75' }}>"{lastParams.keyword}"</span></> : null}
                  </div>
                </div>
                <div className="no-print btn-row" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button type="button" style={actionBtn} onClick={handleNewScan}>New scan</button>
                  <button type="button" style={actionBtn} onClick={handleCopyLink}>{copied ? '✓ Link copied' : 'Copy link'}</button>
                  <button type="button" style={actionBtn} onClick={() => window.print()}>Save as PDF</button>
                </div>
              </div>
              <CompetitorResults data={compData} />
              <AiReport text={compData?.ai_summary} error={compData?.ai_summary_error} />
              {compData?.primary?.content_brief && (
                <ContentBriefPanel brief={compData.primary.content_brief} />
              )}
            </div>
          )}

        </div>

        <div className="landing no-print" style={{ maxWidth: '1120px', margin: '0 auto', padding: '0 16px 64px' }}>
          <section id="features" aria-label="Features"><FeatureRows /></section>
          <div style={{ borderTop: '1px solid #1a1a1a', marginTop: '40px' }} />
          <section id="how-it-works" aria-label="How it works"><HowItWorks /></section>
          <div style={{ borderTop: '1px solid #1a1a1a' }} />
          <section id="score-guide" aria-label="Score guide"><ScoreScale /></section>
          <div style={{ borderTop: '1px solid #1a1a1a' }} />
          <section id="faq" aria-label="FAQ"><FAQSection /></section>
        </div>
      </main>

      <Footer onLegal={setLegalPage} onContact={() => setShowContact(true)} />
      {legalPage && <LegalModal page={legalPage} onClose={() => setLegalPage(null)} />}
      {showContact && <ContactModal onClose={() => setShowContact(false)} />}
    </div>
  )
}
