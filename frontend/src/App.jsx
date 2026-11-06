import { useState } from 'react'
import './index.css'
import { analyzeUrl, findCompetitors } from './api'
import Navbar from './components/Navbar'
import ContactModal from './components/ContactModal'
import Hero from './components/Hero'
import InputForm from './components/InputForm'
import ResultsReport from './components/results/ResultsReport'
import CompetitorResults from './components/competitors/CompetitorResults'
import StatsSection from './components/StatsSection'
import FeaturesSection from './components/FeaturesSection'
import HowItWorks from './components/HowItWorks'
import DeepDiveSection from './components/DeepDiveSection'
import ScoreScale from './components/ScoreScale'
import FAQSection from './components/FAQSection'
import Footer from './components/Footer'
import LegalModal from './components/LegalModal'
import ContentBriefPanel from './components/results/ContentBriefPanel'

function LoadingOverlay({ progress }) {
  const steps = progress?.steps || []
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '64px 24px',
        gap: '20px',
      }}
    >
      <div className="spinner" />
      <div style={{ fontSize: '14px', color: '#c0c0c0', letterSpacing: '0.04em' }} aria-live="polite">
        {progress?.step ? `${progress.step}…` : 'Starting your scan…'}
      </div>
      {steps.length > 1 && (
        <ol style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px', color: '#8a8a8a' }}>
          {steps.slice(0, -1).map((s, i) => (
            <li key={i}><span style={{ color: '#22c55e' }}>✓</span> {s}</li>
          ))}
        </ol>
      )}
      {progress?.elapsed > 0 && (
        <div style={{ fontSize: '11px', color: '#8a8a8a' }}>{Math.round(progress.elapsed)} s elapsed</div>
      )}
    </div>
  )
}

function ErrorBanner({ message }) {
  return (
    <div
      style={{
        background: 'rgba(230,57,70,0.08)',
        border: '1px solid rgba(230,57,70,0.3)',
        borderRadius: '10px',
        padding: '16px 20px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        maxWidth: '700px',
        margin: '24px auto 0',
      }}
    >
      <span style={{ fontSize: '20px' }}>❌</span>
      <div>
        <div style={{ fontSize: '13px', fontWeight: 700, color: '#e63946', marginBottom: '2px' }}>Error</div>
        <div style={{ fontSize: '13px', color: '#a0a0a0' }}>{message}</div>
      </div>
    </div>
  )
}

// Minimal markdown renderer for the Gemini report: ## headings, - bullets, **bold**.
// React escapes all text, so model output can never inject HTML.
function renderInline(text) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={i} style={{ color: '#e0e0e0' }}>{part.slice(2, -2)}</strong>
      : part
  )
}

function AiReport({ text }) {
  if (!text) return null
  const unavailable = /^AI summary (unavailable|error)/i.test(text)
  return (
    <div
      style={{
        background: 'rgba(230,57,70,0.05)',
        border: '1px solid rgba(230,57,70,0.2)',
        borderRadius: '12px',
        padding: '20px',
        marginTop: '24px',
      }}
    >
      <div style={{ fontSize: '11px', color: '#e63946', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '12px' }}>
        AI STRATEGY REPORT
      </div>
      {unavailable ? (
        <p style={{ fontSize: '13px', color: '#a0a0a0' }}>{text}</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {text.split('\n').map((raw, i) => {
            const line = raw.trim()
            if (!line) return null
            const h = line.match(/^#{1,4}\s+(.*)/)
            if (h) return (
              <div key={i} style={{ fontSize: '14px', fontWeight: 700, color: '#fff', marginTop: i ? '12px' : 0 }}>
                {renderInline(h[1])}
              </div>
            )
            const b = line.match(/^(?:[-*•]|\d+[.)])\s+(.*)/)
            if (b) return (
              <div key={i} style={{ fontSize: '13px', color: '#a0a0a0', lineHeight: '1.6', paddingLeft: '14px', position: 'relative' }}>
                <span style={{ position: 'absolute', left: 0, color: '#e63946' }}>•</span>
                {renderInline(b[1])}
              </div>
            )
            return <p key={i} style={{ fontSize: '13px', color: '#a0a0a0', lineHeight: '1.6' }}>{renderInline(line)}</p>
          })}
        </div>
      )}
    </div>
  )
}

function ExecutiveSummary({ summary, url }) {
  if (!summary) return null
  return (
    <div
      style={{
        background: 'rgba(230,57,70,0.05)',
        border: '1px solid rgba(230,57,70,0.2)',
        borderRadius: '12px',
        padding: '20px',
        marginTop: '24px',
      }}
    >
      <div style={{ fontSize: '11px', color: '#e63946', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '12px' }}>
        SUMMARY
      </div>
      {typeof summary === 'string' ? (
        <p style={{ fontSize: '13px', color: '#a0a0a0', lineHeight: '1.6' }}>{summary}</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {Object.entries(summary).map(([k, v]) => (
            <div key={k}>
              <span style={{ fontSize: '11px', fontWeight: 700, color: '#606060', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                {k.replace(/_/g, ' ')}:{' '}
              </span>
              <span style={{ fontSize: '13px', color: '#a0a0a0' }}>{String(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [seoData, setSeoData] = useState(null)
  const [compData, setCompData] = useState(null)
  const [mode, setMode] = useState(null) // 'seo' | 'competitors'
  const [legalPage, setLegalPage] = useState(null)
  const [analyzeParams, setAnalyzeParams] = useState(null)
  const [showContact, setShowContact] = useState(false)
  const [progress, setProgress] = useState(null)

  async function handleAnalyze({ url, keyword, crawlMode, geo, userApiKeys }) {
    setLoading(true)
    setError(null)
    setSeoData(null)
    setCompData(null)
    setMode('seo')
    setAnalyzeParams({ url, keyword, crawlMode, geo })
    setProgress(null)
    try {
      const result = await analyzeUrl({ url, keyword, geo, crawlMode, userApiKeys, onProgress: setProgress })
      setSeoData(result)
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to analyze URL. Make sure the backend is running.')
      setMode(null)
    } finally {
      setLoading(false)
    }
  }

  async function handleCompetitors({ url, keyword, userApiKeys }) {
    setLoading(true)
    setError(null)
    setSeoData(null)
    setCompData(null)
    setMode('competitors')
    setProgress(null)
    try {
      const result = await findCompetitors({ url, keyword, userApiKeys, onProgress: setProgress })
      setCompData(result)
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'Failed to fetch competitors. Make sure the backend is running.')
      setMode(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0a', paddingTop: '60px' }}>
      <Navbar />

      {/* Demo mode banner */}
      <div style={{
        background: 'rgba(234,179,8,0.07)',
        borderBottom: '1px solid rgba(234,179,8,0.2)',
        padding: '9px 24px',
        textAlign: 'center',
        fontSize: '12px',
        color: '#a08830',
        letterSpacing: '0.02em',
      }}>
        <span style={{ fontWeight: 700, color: '#eab308' }}>🚧 Work in progress</span>
        {' '}— Everything on the site works. Feel free to try the tool! Free checks come from a shared daily pool — add your own API keys for unlimited use.
      </div>

      <div id="section-top" />
      <Hero />

      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '0 24px 80px' }}>
        <InputForm onAnalyze={handleAnalyze} onCompetitors={handleCompetitors} loading={loading} />

        {error && <ErrorBanner message={error} />}

        {loading && <LoadingOverlay progress={progress} />}

        {!seoData && !compData && !loading && (
          <div>
            <div style={{ borderTop: '1px solid #1a1a1a', marginTop: '40px' }} />
            <StatsSection />
            <div style={{ borderTop: '1px solid #1a1a1a' }} />
            <div id="section-features"><FeaturesSection /></div>
            <div style={{ borderTop: '1px solid #1a1a1a' }} />
            <div id="section-how"><HowItWorks /></div>
            <DeepDiveSection />
            <div style={{ borderTop: '1px solid #1a1a1a' }} />
            <div id="section-scale"><ScoreScale /></div>
            <div style={{ borderTop: '1px solid #1a1a1a' }} />
            <div id="section-faq"><FAQSection /></div>
          </div>
        )}

        {!loading && seoData && (
          <div className="fade-in">
            {/* Page header bar */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: '#161616',
                border: '1px solid #2a2a2a',
                borderRadius: '10px',
                padding: '14px 18px',
                marginTop: '24px',
              }}
            >
              <div>
                <div style={{ fontSize: '11px', color: '#606060', letterSpacing: '0.06em', marginBottom: '2px' }}>ANALYZING</div>
                <div style={{ fontSize: '13px', color: '#fff', fontWeight: 600 }}>{seoData.url}</div>
              </div>
              {seoData.keyword && (
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '11px', color: '#606060', letterSpacing: '0.06em', marginBottom: '2px' }}>KEYWORD</div>
                  <div style={{ fontSize: '13px', color: '#e63946', fontWeight: 600 }}>"{seoData.keyword}"</div>
                </div>
              )}
            </div>

            <ExecutiveSummary summary={seoData.summary} url={seoData.url} />
            <ResultsReport data={seoData} />
          </div>
        )}

        {!loading && compData && mode === 'competitors' && (
          <div className="fade-in">
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: '#161616',
                border: '1px solid #2a2a2a',
                borderRadius: '10px',
                padding: '14px 18px',
                marginTop: '24px',
              }}
            >
              <div>
                <div style={{ fontSize: '11px', color: '#606060', letterSpacing: '0.06em', marginBottom: '2px' }}>COMPETITOR ANALYSIS</div>
                <div style={{ fontSize: '13px', color: '#fff', fontWeight: 600 }}>
                  {Array.isArray(compData) ? compData.length : (compData?.competitors?.length ?? '?')} competitors found
                </div>
              </div>
            </div>
            <AiReport text={compData?.ai_summary} />
            {compData?.primary?.content_brief && (
              <ContentBriefPanel brief={compData.primary.content_brief} />
            )}
            <CompetitorResults data={compData} />
          </div>
        )}
      </div>

      <Footer onLegal={setLegalPage} onContact={() => setShowContact(true)} />
      {legalPage && <LegalModal page={legalPage} onClose={() => setLegalPage(null)} />}
      {showContact && <ContactModal onClose={() => setShowContact(false)} />}
    </div>
  )
}
