import { useState, useEffect } from 'react'
import { getRateStatus, resetTimeLocal } from '../api'

const DEFAULT_LIMIT = 3     // replaced by /rate-status scans_limit once loaded

const SERPER_RE = /^[a-f0-9]{40}$/
const GEMINI_RE = /^AIzaSy[A-Za-z0-9_-]{33}$/

const inputStyle = {
  width: '100%',
  background: '#111',
  border: '1px solid #2a2a2a',
  borderRadius: '8px',
  padding: '12px 16px',
  color: '#fff',
  fontSize: '14px',
  transition: 'border-color 0.15s',
}

const labelStyle = {
  display: 'block',
  fontSize: '11px',
  fontWeight: 700,
  letterSpacing: '0.1em',
  color: 'var(--text-muted)',
  marginBottom: '8px',
  textTransform: 'uppercase',
}

const hintStyle = { fontSize: '11px', color: 'var(--text-muted)', marginTop: '6px' }

function normalizeUrl(raw) {
  const u = String(raw || '').trim()
  if (!u) return ''
  return /^https?:\/\//i.test(u) ? u : `https://${u.replace(/^\/+/, '')}`
}

function ToggleBtn({ pressed, onClick, children }) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      style={{
        background: pressed ? 'rgba(230,57,70,0.1)' : '#161616',
        border: `1px solid ${pressed ? 'rgba(230,57,70,0.4)' : '#2a2a2a'}`,
        borderRadius: '6px', padding: '6px 12px', cursor: 'pointer',
        fontSize: '11px', fontWeight: 700,
        color: pressed ? '#ff6b75' : 'var(--text-body)',
        transition: 'all 0.15s',
      }}
    >{children}</button>
  )
}

export default function InputForm({
  onAnalyze, onCompetitors, loading,
  activeTab = 'check', onTabChange, urlRef, initial, refreshKey,
}) {
  const [url, setUrl] = useState(initial?.url ?? '')
  const [keyword, setKeyword] = useState(initial?.keyword ?? '')
  const [focusedUrl, setFocusedUrl] = useState(false)
  const [focusedKw, setFocusedKw] = useState(false)
  const [globalUsed, setGlobalUsed] = useState(null)   // this visitor's scans today; null = loading
  const [globalLimit, setGlobalLimit] = useState(DEFAULT_LIMIT)
  const [resetsAt, setResetsAt] = useState(null)
  const [paused, setPaused] = useState(false)
  const [comparisonsLeft, setComparisonsLeft] = useState(null)
  const [showTooltip, setShowTooltip] = useState(false)
  const [crawlMode, setCrawlMode] = useState('standard')
  const [geoMode, setGeoMode] = useState(false)
  const [formError, setFormError] = useState(null)

  // User-supplied API keys (kept in memory only)
  const [geminiKey, setGeminiKey] = useState('')
  const [serperKey, setSerperKey] = useState('')

  const setActiveTab = id => onTabChange?.(id)

  useEffect(() => {
    let alive = true
    getRateStatus()
      .then(data => {
        if (!alive) return
        if (data?.ip_used != null) setGlobalUsed(data.ip_used)
        if (data?.daily_limit) setGlobalLimit(data.daily_limit)
        if (data?.resets_at) setResetsAt(data.resets_at)
        setPaused(!!data?.paused)
        if (data?.comparisons_remaining != null) setComparisonsLeft(data.comparisons_remaining)
      })
      .catch(() => { if (alive) setGlobalUsed(v => v ?? 0) })
    return () => { alive = false }
  }, [refreshKey])

  const checksUsed = globalUsed ?? 0
  const checksLeft = Math.max(0, globalLimit - checksUsed)
  const limitReached = globalUsed !== null && (checksLeft === 0 || paused)
  const geminiOk = GEMINI_RE.test(geminiKey.trim())
  const serperOk = SERPER_RE.test(serperKey.trim())
  const hasOwnKeys = geminiOk && serperOk
  const blocked = !hasOwnKeys && limitReached
  // Competitor comparisons have their own daily allowance, separate from page scans
  const compareBlocked = !hasOwnKeys && (paused || comparisonsLeft === 0)

  function userApiKeys() {
    return hasOwnKeys ? { gemini_key: geminiKey.trim(), serper_key: serperKey.trim() } : undefined
  }

  function run(mode) {
    setFormError(null)
    const cleanUrl = normalizeUrl(url)
    if (!cleanUrl) {
      setFormError('Enter the page URL you want to check.')
      urlRef?.current?.focus()
      return
    }
    if (mode === 'competitors' && !keyword.trim()) {
      setFormError('Add a target keyword to find competitors.')
      document.getElementById('kw-input')?.focus()
      return
    }
    if (mode === 'competitors' ? compareBlocked : blocked) return
    if (cleanUrl !== url) setUrl(cleanUrl)
    if (!hasOwnKeys) {
      if (mode === 'competitors') setComparisonsLeft(v => Math.max(0, (v ?? 1) - 1))
      else setGlobalUsed(v => (v ?? 0) + 1)
    }
    const params = { url: cleanUrl, keyword: keyword.trim(), crawlMode, geo: geoMode, userApiKeys: userApiKeys() }
    if (mode === 'competitors') onCompetitors(params)
    else onAnalyze(params)
  }

  function handleSubmit(e) {
    e.preventDefault()
    run('analyze')
  }

  const tabBtn = (id, label) => (
    <button
      type="button"
      role="tab"
      id={`tab-${id}`}
      aria-selected={activeTab === id}
      aria-controls={`panel-${id}`}
      onClick={() => setActiveTab(id)}
      style={{
        flex: 1,
        padding: '10px 4px',
        fontSize: '12px',
        fontWeight: 700,
        letterSpacing: '0.07em',
        border: 'none',
        borderBottom: `2px solid ${activeTab === id ? '#e63946' : 'transparent'}`,
        background: 'transparent',
        color: activeTab === id ? '#ff6b75' : 'var(--text-body)',
        cursor: 'pointer',
        transition: 'all 0.15s',
      }}
    >
      {label}
    </button>
  )

  const disabled = loading || blocked
  const compareDisabled = loading || compareBlocked

  return (
    <div
      className="input-form no-print"
      style={{
        background: '#161616',
        border: '1px solid #2a2a2a',
        borderRadius: '12px',
        maxWidth: '760px',
        margin: '0 auto',
      }}
    >
      {/* Tab bar */}
      <div
        role="tablist"
        aria-label="Scan options"
        style={{ display: 'flex', borderBottom: '1px solid #2a2a2a', background: '#111', borderRadius: '12px 12px 0 0' }}
      >
        {tabBtn('check', 'CHECK PAGE')}
        {tabBtn('apikey', '🔑 ADD YOUR OWN KEYS')}
      </div>

      {/* Pool counter */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '12px',
          padding: '10px 20px',
          borderBottom: '1px solid #1e1e1e',
          background: '#111',
        }}
      >
        {hasOwnKeys ? (
          <span style={{ fontSize: '12px', color: '#4caf50', fontWeight: 700 }}>
            ✓ Using your keys: up to 100 scans a day
          </span>
        ) : (
          <span style={{ fontSize: '12px', color: limitReached ? '#ff6b75' : 'var(--text-body)' }}>
            {globalUsed === null ? 'Loading…' : paused ? (
              <>Free scans are paused for today. Back at {resetTimeLocal(resetsAt)}.</>
            ) : checksLeft === 0 ? (
              <>You&rsquo;ve used today&rsquo;s {globalLimit} free scans. More at {resetTimeLocal(resetsAt)}.</>
            ) : (
              <>
                <span style={{ fontWeight: 700, color: '#ff6b75' }}>{checksLeft} of {globalLimit}</span>{' '}
                free scans left today
              </>
            )}
          </span>
        )}
        <div style={{ position: 'relative' }}>
          <button
            type="button"
            aria-label="About free scans"
            aria-expanded={showTooltip}
            aria-controls="pool-tooltip"
            onClick={() => setShowTooltip(v => !v)}
            onBlur={() => setShowTooltip(false)}
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
            style={{
              width: '20px', height: '20px', borderRadius: '50%', background: '#222',
              border: '1px solid #333', display: 'inline-flex', alignItems: 'center',
              justifyContent: 'center', fontSize: '11px', color: 'var(--text-body)',
              cursor: 'pointer', fontWeight: 700, padding: 0,
            }}
          >?</button>
          {showTooltip && (
            <div id="pool-tooltip" role="tooltip" style={{
              position: 'absolute', right: 0, top: '26px', zIndex: 100,
              background: '#1e1e1e', border: '1px solid #333', borderRadius: '8px',
              padding: '10px 14px', width: '230px', maxWidth: '70vw', fontSize: '12px', color: 'var(--text-body)',
              lineHeight: 1.5, boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
            }}>
              You get {globalLimit} free page scans and 1 competitor comparison a day.
              Rescanning a page after you fix it is free (twice a day per page).
              Resets at {resetTimeLocal(resetsAt)} your time. Add both of your own free keys
              for up to 100 scans a day.
            </div>
          )}
        </div>
      </div>

      {/* ── Tab: Check page ── */}
      <div role="tabpanel" id="panel-check" aria-labelledby="tab-check" hidden={activeTab !== 'check'}>
        {/* Crawl / GEO toggles */}
        <div style={{ padding: '12px 20px', borderBottom: '1px solid #1e1e1e', background: '#0f0f0f' }}>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <ToggleBtn pressed={crawlMode === 'standard'} onClick={() => setCrawlMode('standard')}>Standard crawl</ToggleBtn>
            <ToggleBtn pressed={crawlMode === 'javascript'} onClick={() => setCrawlMode('javascript')}>JS rendering</ToggleBtn>
            <ToggleBtn pressed={geoMode} onClick={() => setGeoMode(g => !g)}>GEO analysis</ToggleBtn>
          </div>
          <div style={{ ...hintStyle, lineHeight: 1.5 }}>
            JS rendering for sites built with JavaScript (slower) · GEO checks whether AI search like ChatGPT can read your page
          </div>
        </div>

        <div style={{ padding: '18px 20px 20px' }} className="form-body">
          {blocked && (
            <div
              role="status"
              style={{
                background: 'rgba(230,57,70,0.08)', border: '1px solid rgba(230,57,70,0.25)',
                borderRadius: '8px', padding: '12px 16px', marginBottom: '16px',
                fontSize: '13px', color: '#ff6b75',
              }}
            >
              Today's free page scans are used up{comparisonsLeft > 0 ? ' (you can still run 1 competitor comparison)' : ''}.{' '}
              <button
                type="button"
                onClick={() => setActiveTab('apikey')}
                style={{ background: 'none', border: 'none', color: '#ff8a92', fontWeight: 700, cursor: 'pointer', textDecoration: 'underline', fontSize: '13px', padding: 0 }}
              >
                Add your own free keys
              </button>{' '}for up to 100 scans a day.
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="field-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: '0 14px' }}>
            <div style={{ marginBottom: '16px' }}>
              <label htmlFor="url-input" style={labelStyle}>Website URL</label>
              <input
                id="url-input"
                ref={urlRef}
                type="text"
                inputMode="url"
                autoComplete="url"
                autoCapitalize="off"
                spellCheck={false}
                placeholder="example.com/page"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onFocus={() => setFocusedUrl(true)}
                onBlur={() => { setFocusedUrl(false); if (url.trim()) setUrl(normalizeUrl(url)) }}
                style={{ ...inputStyle, borderColor: focusedUrl ? '#e63946' : '#2a2a2a' }}
                required
                aria-describedby={formError ? 'form-error' : undefined}
              />
            </div>

            <div style={{ marginBottom: '20px' }}>
              <label htmlFor="kw-input" style={labelStyle}>Target Keyword</label>
              <input
                id="kw-input"
                type="text"
                placeholder="e.g. seo audit tool"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onFocus={() => setFocusedKw(true)}
                onBlur={() => setFocusedKw(false)}
                style={{ ...inputStyle, borderColor: focusedKw ? '#e63946' : '#2a2a2a' }}
                aria-describedby="kw-hint"
              />
              <div id="kw-hint" style={hintStyle}>Optional for a page check. Required to find competitors.</div>
            </div>
            </div>

            {formError && (
              <div id="form-error" role="alert" style={{ fontSize: '13px', color: '#ff6b75', marginBottom: '14px' }}>
                {formError}
              </div>
            )}

            <div className="form-actions">
              <button
                type="submit"
                disabled={disabled}
                style={{
                  background: loading ? '#7a1920' : blocked ? '#333' : '#e63946',
                  color: blocked ? '#8a8a8a' : '#fff',
                  border: 'none', borderRadius: '8px', padding: '13px',
                  fontWeight: 700, fontSize: '13px', letterSpacing: '0.06em',
                  cursor: disabled ? 'not-allowed' : 'pointer',
                  transition: 'background 0.15s',
                }}
              >
                {loading ? '⏳ ANALYZING...' : '🔍 ANALYZE SEO'}
              </button>

              <button
                type="button"
                onClick={() => run('competitors')}
                disabled={compareDisabled}
                title={compareBlocked && !loading ? "You've used today's free competitor comparison." : undefined}
                style={{
                  background: 'transparent',
                  color: compareBlocked ? '#8a8a8a' : '#ff6b75',
                  border: `1px solid ${compareBlocked ? '#333' : 'rgba(230,57,70,0.4)'}`,
                  borderRadius: '8px', padding: '13px', fontWeight: 700, fontSize: '13px',
                  letterSpacing: '0.06em',
                  cursor: compareDisabled ? 'not-allowed' : 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                {loading ? '⏳ LOADING...' : '🏆 FIND COMPETITORS'}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* ── Tab: Add your own keys ── */}
      <div role="tabpanel" id="panel-apikey" aria-labelledby="tab-apikey" hidden={activeTab !== 'apikey'} style={{ padding: '24px 20px' }}>
        <p style={{ fontSize: '13px', color: 'var(--text-body)', marginBottom: '20px', lineHeight: 1.6 }}>
          Add both keys (both are free) to get up to 100 scans a day of your own instead of the 3 free ones.
          Keys stay in this browser tab and are sent with each scan over HTTPS.
        </p>

        <div style={{ marginBottom: '16px' }}>
          <label htmlFor="gemini-key" style={labelStyle}>Gemini API Key</label>
          <input
            id="gemini-key"
            type="password"
            autoComplete="off"
            placeholder="Paste your Gemini API key"
            value={geminiKey}
            onChange={(e) => setGeminiKey(e.target.value)}
            style={inputStyle}
            aria-describedby="gemini-hint"
            aria-invalid={geminiKey.trim() !== '' && !geminiOk}
          />
          <div id="gemini-hint" style={{ ...hintStyle, color: geminiKey.trim() && !geminiOk ? '#ff6b75' : hintStyle.color }}>
            {geminiKey.trim() && !geminiOk
              ? "That doesn't look like a Gemini key (it starts with AIzaSy and is 39 characters)."
              : 'Get a free key at aistudio.google.com'}
          </div>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <label htmlFor="serper-key" style={labelStyle}>Serper API Key</label>
          <input
            id="serper-key"
            type="password"
            autoComplete="off"
            placeholder="Paste your Serper API key"
            value={serperKey}
            onChange={(e) => setSerperKey(e.target.value)}
            style={inputStyle}
            aria-describedby="serper-hint"
            aria-invalid={serperKey.trim() !== '' && !serperOk}
          />
          <div id="serper-hint" style={{ ...hintStyle, color: serperKey.trim() && !serperOk ? '#ff6b75' : hintStyle.color }}>
            {serperKey.trim() && !serperOk
              ? "That doesn't look like a Serper key (40 lowercase letters and numbers)."
              : 'Get a free key at serper.dev'}
          </div>
        </div>

        <button
          type="button"
          onClick={() => { setActiveTab('check'); setTimeout(() => urlRef?.current?.focus(), 0) }}
          disabled={!hasOwnKeys}
          style={{
            background: hasOwnKeys ? '#e63946' : '#333',
            color: hasOwnKeys ? '#fff' : '#8a8a8a', border: 'none', borderRadius: '8px',
            padding: '12px 24px', fontWeight: 700, fontSize: '13px',
            letterSpacing: '0.06em', cursor: hasOwnKeys ? 'pointer' : 'not-allowed', transition: 'background 0.2s',
            width: '100%',
          }}
        >
          Use these keys
        </button>

        <div role="status" style={{
          marginTop: '14px', borderRadius: '8px', padding: '10px 14px', fontSize: '12px',
          background: hasOwnKeys ? 'rgba(76,175,80,0.08)' : 'transparent',
          border: hasOwnKeys ? '1px solid rgba(76,175,80,0.25)' : '1px solid transparent',
          color: hasOwnKeys ? '#4caf50' : 'var(--text-muted)',
        }}>
          {hasOwnKeys
            ? '✓ Both keys look right. Your scans will use your keys: up to 100 scans a day.'
            : (geminiKey.trim() || serperKey.trim())
              ? 'Add both keys to use your own quota. Until then, scans use your free daily allowance.'
              : ''}
        </div>
      </div>
    </div>
  )
}
