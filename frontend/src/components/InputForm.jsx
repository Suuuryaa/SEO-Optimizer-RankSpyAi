import { useState, useEffect } from 'react'
import { getRateStatus } from '../api'

const DEFAULT_LIMIT = 100   // replaced by /rate-status daily_limit once loaded

const inputStyle = {
  width: '100%',
  background: '#111',
  border: '1px solid #2a2a2a',
  borderRadius: '8px',
  padding: '12px 16px',
  color: '#fff',
  fontSize: '14px',
  outline: 'none',
  transition: 'border-color 0.15s',
}

const labelStyle = {
  display: 'block',
  fontSize: '11px',
  fontWeight: 700,
  letterSpacing: '0.1em',
  color: '#606060',
  marginBottom: '8px',
  textTransform: 'uppercase',
}

export default function InputForm({ onAnalyze, onCompetitors, loading }) {
  const [url, setUrl] = useState('')
  const [keyword, setKeyword] = useState('')
  const [focusedUrl, setFocusedUrl] = useState(false)
  const [focusedKw, setFocusedKw] = useState(false)
  const [globalUsed, setGlobalUsed] = useState(null)   // null = loading
  const [GLOBAL_LIMIT, setGlobalLimit] = useState(DEFAULT_LIMIT)
  const [showTooltip, setShowTooltip] = useState(false)
  const [crawlMode, setCrawlMode] = useState('standard')
  const [geoMode, setGeoMode] = useState(false)
  const [activeTab, setActiveTab] = useState('check')  // 'check' | 'apikey'

  // User-supplied API keys
  const [geminiKey, setGeminiKey] = useState('')
  const [serperKey, setSerperKey] = useState('')
  const [keySaved, setKeySaved] = useState(false)

  useEffect(() => {
    getRateStatus()
      .then(data => {
        if (data?.ip_used != null) setGlobalUsed(data.ip_used)
        if (data?.daily_limit) setGlobalLimit(data.daily_limit)
      })
      .catch(() => setGlobalUsed(0))
  }, [])

  const checksUsed = globalUsed ?? 0
  const checksLeft = Math.max(0, GLOBAL_LIMIT - checksUsed)
  const limitReached = checksLeft === 0
  const hasOwnKeys = geminiKey.trim() || serperKey.trim()

  function userApiKeys() {
    const keys = {}
    if (geminiKey.trim()) keys.gemini_key = geminiKey.trim()
    if (serperKey.trim()) keys.serper_key = serperKey.trim()
    return Object.keys(keys).length > 0 ? keys : undefined
  }

  function refreshGlobalCount() {
    getRateStatus()
      .then(data => {
        if (data?.ip_used != null) setGlobalUsed(data.ip_used)
        if (data?.daily_limit) setGlobalLimit(data.daily_limit)
      })
      .catch(() => {})
  }

  function handleAnalyze(e) {
    e.preventDefault()
    if (!url.trim()) return
    if (!hasOwnKeys && limitReached) return
    if (!hasOwnKeys) setGlobalUsed(v => (v ?? 0) + 1)
    refreshGlobalCount()
    onAnalyze({ url: url.trim(), keyword: keyword.trim(), crawlMode, geo: geoMode, userApiKeys: userApiKeys() })
  }

  function handleCompetitors(e) {
    e.preventDefault()
    if (!url.trim()) return
    if (!hasOwnKeys && limitReached) return
    if (!hasOwnKeys) setGlobalUsed(v => (v ?? 0) + 1)
    refreshGlobalCount()
    onCompetitors({ url: url.trim(), keyword: keyword.trim(), crawlMode, userApiKeys: userApiKeys() })
  }

  function handleSaveKeys() {
    setKeySaved(true)
    setTimeout(() => setKeySaved(false), 2500)
  }

  const tabBtn = (id, label) => (
    <button
      type="button"
      onClick={() => setActiveTab(id)}
      style={{
        flex: 1,
        padding: '10px 0',
        fontSize: '12px',
        fontWeight: 700,
        letterSpacing: '0.07em',
        border: 'none',
        borderBottom: `2px solid ${activeTab === id ? '#e63946' : 'transparent'}`,
        background: 'transparent',
        color: activeTab === id ? '#e63946' : '#555',
        cursor: 'pointer',
        transition: 'all 0.15s',
      }}
    >
      {label}
    </button>
  )

  return (
    <div
      style={{
        background: '#161616',
        border: '1px solid #2a2a2a',
        borderRadius: '12px',
        overflow: 'hidden',
        maxWidth: '700px',
        margin: '32px auto',
      }}
    >
      {/* Tab bar */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid #2a2a2a',
          background: '#111',
        }}
      >
        {tabBtn('check', 'CHECK PAGE')}
        {tabBtn('apikey', '🔑 ADD YOUR OWN KEY')}
      </div>

      {/* Pool counter */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '10px 20px',
          borderBottom: '1px solid #1e1e1e',
          background: '#111',
        }}
      >
        {hasOwnKeys ? (
          <span style={{ fontSize: '12px', color: '#4caf50', fontWeight: 700 }}>
            ✓ Using your own API key — unlimited checks
          </span>
        ) : (
          <span style={{ fontSize: '12px', color: limitReached ? '#e63946' : '#a0a0a0' }}>
            {globalUsed === null ? 'Loading...' : (
              <>
                You have{' '}
                <span style={{ fontWeight: 700, color: '#e63946' }}>
                  {checksLeft} of {GLOBAL_LIMIT}
                </span>{' '}
                checks left (demo)
              </>
            )}
          </span>
        )}
        <div style={{ position: 'relative' }}>
          <span
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
            style={{
              width: '16px', height: '16px', borderRadius: '50%', background: '#222',
              border: '1px solid #333', display: 'inline-flex', alignItems: 'center',
              justifyContent: 'center', fontSize: '10px', color: '#606060',
              cursor: 'default', fontWeight: 700,
            }}
          >?</span>
          {showTooltip && (
            <div style={{
              position: 'absolute', right: 0, top: '24px', zIndex: 100,
              background: '#1e1e1e', border: '1px solid #333', borderRadius: '8px',
              padding: '10px 14px', width: '230px', fontSize: '12px', color: '#a0a0a0',
              lineHeight: 1.5, boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
            }}>
              {GLOBAL_LIMIT} free checks per day, shared across all users. Resets daily at midnight UTC.
              Add your own API keys for unlimited access.
            </div>
          )}
        </div>
      </div>

      {/* ── Tab: Check page ── */}
      {activeTab === 'check' && (
        <div>
          {/* Crawl / GEO toggles */}
          <div style={{ padding: '12px 20px', borderBottom: '1px solid #1e1e1e', background: '#0f0f0f', display: 'flex', gap: '8px' }}>
            {[
              { val: 'standard', label: 'Standard crawl' },
              { val: 'javascript', label: 'JS rendering' },
            ].map(opt => (
              <button
                key={opt.val}
                type="button"
                onClick={() => setCrawlMode(opt.val)}
                style={{
                  background: crawlMode === opt.val ? 'rgba(230,57,70,0.1)' : '#161616',
                  border: `1px solid ${crawlMode === opt.val ? 'rgba(230,57,70,0.4)' : '#2a2a2a'}`,
                  borderRadius: '6px', padding: '6px 12px', cursor: 'pointer',
                  fontSize: '11px', fontWeight: 700,
                  color: crawlMode === opt.val ? '#e63946' : '#666',
                  transition: 'all 0.15s',
                }}
              >{opt.label}</button>
            ))}
            <button
              type="button"
              onClick={() => setGeoMode(g => !g)}
              style={{
                background: geoMode ? 'rgba(230,57,70,0.1)' : '#161616',
                border: `1px solid ${geoMode ? 'rgba(230,57,70,0.4)' : '#2a2a2a'}`,
                borderRadius: '6px', padding: '6px 12px', cursor: 'pointer',
                fontSize: '11px', fontWeight: 700,
                color: geoMode ? '#e63946' : '#666', transition: 'all 0.15s',
              }}
            >GEO analysis</button>
          </div>

          <div style={{ padding: '24px 28px 28px' }}>
            {!hasOwnKeys && limitReached && (
              <div
                style={{
                  background: 'rgba(230,57,70,0.08)', border: '1px solid rgba(230,57,70,0.25)',
                  borderRadius: '8px', padding: '12px 16px', marginBottom: '16px',
                  fontSize: '13px', color: '#e63946',
                }}
              >
                All {GLOBAL_LIMIT} demo checks have been used.{' '}
                <button
                  type="button"
                  onClick={() => setActiveTab('apikey')}
                  style={{ background: 'none', border: 'none', color: '#ff6b75', fontWeight: 700, cursor: 'pointer', textDecoration: 'underline', fontSize: '13px', padding: 0 }}
                >
                  Add your own API key
                </button>{' '}for unlimited access.
              </div>
            )}

            <form>
              <div style={{ marginBottom: '16px' }}>
                <label style={labelStyle}>Website URL</label>
                <input
                  type="url"
                  placeholder="https://example.com"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  onFocus={() => setFocusedUrl(true)}
                  onBlur={() => setFocusedUrl(false)}
                  style={{ ...inputStyle, borderColor: focusedUrl ? '#e63946' : '#2a2a2a' }}
                  required
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={labelStyle}>Target Keyword</label>
                <input
                  type="text"
                  placeholder="e.g. seo audit tool"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  onFocus={() => setFocusedKw(true)}
                  onBlur={() => setFocusedKw(false)}
                  style={{ ...inputStyle, borderColor: focusedKw ? '#e63946' : '#2a2a2a' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <button
                  type="submit"
                  onClick={handleAnalyze}
                  disabled={loading || !url.trim() || (!hasOwnKeys && limitReached)}
                  style={{
                    background: loading ? '#7a1920' : (!hasOwnKeys && limitReached) ? '#333' : '#e63946',
                    color: (!hasOwnKeys && limitReached) ? '#666' : '#fff',
                    border: 'none', borderRadius: '8px', padding: '13px',
                    fontWeight: 700, fontSize: '13px', letterSpacing: '0.06em',
                    cursor: (loading || !url.trim() || (!hasOwnKeys && limitReached)) ? 'not-allowed' : 'pointer',
                    transition: 'background 0.15s', opacity: !url.trim() ? 0.5 : 1,
                  }}
                >
                  {loading ? '⏳ ANALYZING...' : '🔍 ANALYZE SEO'}
                </button>

                <button
                  type="button"
                  onClick={handleCompetitors}
                  disabled={loading || !url.trim() || (!hasOwnKeys && limitReached)}
                  style={{
                    background: 'transparent',
                    color: (!hasOwnKeys && limitReached) ? '#444' : '#e63946',
                    border: `1px solid ${(!hasOwnKeys && limitReached) ? '#333' : 'rgba(230,57,70,0.4)'}`,
                    borderRadius: '8px', padding: '13px', fontWeight: 700, fontSize: '13px',
                    letterSpacing: '0.06em',
                    cursor: (loading || !url.trim() || (!hasOwnKeys && limitReached)) ? 'not-allowed' : 'pointer',
                    transition: 'all 0.15s', opacity: !url.trim() ? 0.5 : 1,
                  }}
                >
                  {loading ? '⏳ LOADING...' : '🏆 FIND COMPETITORS'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Tab: Add your own key ── */}
      {activeTab === 'apikey' && (
        <div style={{ padding: '24px 28px 28px' }}>
          <p style={{ fontSize: '13px', color: '#a0a0a0', marginBottom: '20px', lineHeight: 1.6 }}>
            Enter your own API keys to bypass the shared demo limit and get unlimited checks.
            Keys are only used for your requests and never stored on our servers.
          </p>

          <div style={{ marginBottom: '16px' }}>
            <label style={labelStyle}>Gemini API Key</label>
            <input
              type="password"
              placeholder="AIzaSy..."
              value={geminiKey}
              onChange={(e) => { setGeminiKey(e.target.value); setKeySaved(false) }}
              style={inputStyle}
            />
            <div style={{ fontSize: '11px', color: '#444', marginTop: '6px' }}>
              Get a free key at aistudio.google.com
            </div>
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label style={labelStyle}>Serper API Key (for competitor search)</label>
            <input
              type="password"
              placeholder="your serper key..."
              value={serperKey}
              onChange={(e) => { setSerperKey(e.target.value); setKeySaved(false) }}
              style={inputStyle}
            />
            <div style={{ fontSize: '11px', color: '#444', marginTop: '6px' }}>
              Get a free key at serper.dev
            </div>
          </div>

          <button
            type="button"
            onClick={handleSaveKeys}
            disabled={!geminiKey.trim() && !serperKey.trim()}
            style={{
              background: keySaved ? '#1a4a1a' : '#e63946',
              color: '#fff', border: 'none', borderRadius: '8px',
              padding: '12px 24px', fontWeight: 700, fontSize: '13px',
              letterSpacing: '0.06em', cursor: 'pointer', transition: 'background 0.2s',
              width: '100%',
            }}
          >
            {keySaved ? '✓ KEY SAVED — SWITCH TO CHECK PAGE TAB' : 'SAVE KEYS & USE MY API'}
          </button>

          {hasOwnKeys && (
            <div style={{
              marginTop: '14px', background: 'rgba(76,175,80,0.08)',
              border: '1px solid rgba(76,175,80,0.25)', borderRadius: '8px',
              padding: '10px 14px', fontSize: '12px', color: '#4caf50',
            }}>
              ✓ Your keys are active. Switch to the "Check Page" tab to analyze a site.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
