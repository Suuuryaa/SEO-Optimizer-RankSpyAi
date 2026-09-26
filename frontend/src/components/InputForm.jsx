import { useState, useEffect, useRef } from 'react'
import { getRateStatus } from '../api'

const DAILY_LIMIT = 10
const STORAGE_KEY = 'rankspy_checks'

function getChecksToday() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return 0
    const { date, count } = JSON.parse(raw)
    const today = new Date().toISOString().slice(0, 10)
    return date === today ? count : 0
  } catch {
    return 0
  }
}

function saveChecksToday(count) {
  const today = new Date().toISOString().slice(0, 10)
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ date: today, count }))
}

function incrementChecks() {
  const count = getChecksToday() + 1
  saveChecksToday(count)
  return count
}

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
  const [checksUsed, setChecksUsed] = useState(0)
  const [showSettings, setShowSettings] = useState(false)
  const [crawlMode, setCrawlMode] = useState('standard')
  const [geoMode, setGeoMode] = useState(false)
  const [showTooltip, setShowTooltip] = useState(false)

  useEffect(() => {
    // Seed from localStorage immediately (optimistic), then sync from server
    setChecksUsed(getChecksToday())
    getRateStatus()
      .then(data => {
        if (data?.ip_used != null) {
          setChecksUsed(data.ip_used)
          saveChecksToday(data.ip_used)
        }
      })
      .catch(() => { /* keep localStorage value on failure */ })
  }, [])

  const checksLeft = Math.max(0, DAILY_LIMIT - checksUsed)
  const limitReached = checksLeft === 0

  function _syncRateStatus() {
    getRateStatus()
      .then(data => { if (data?.ip_used != null) setChecksUsed(data.ip_used) })
      .catch(() => { /* keep optimistic value on failure */ })
  }

  function handleAnalyze(e) {
    e.preventDefault()
    if (!url.trim() || limitReached) return
    const newCount = incrementChecks()
    setChecksUsed(newCount)          // optimistic update
    _syncRateStatus()                // background sync from server
    onAnalyze({ url: url.trim(), keyword: keyword.trim(), crawlMode, geo: geoMode })
  }

  function handleCompetitors(e) {
    e.preventDefault()
    if (!url.trim() || limitReached) return
    const newCount = incrementChecks()
    setChecksUsed(newCount)          // optimistic update
    _syncRateStatus()                // background sync from server
    onCompetitors({ url: url.trim(), keyword: keyword.trim(), crawlMode })
  }

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
      {/* Header bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '14px 20px',
          borderBottom: '1px solid #2a2a2a',
          background: '#111',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#fff', letterSpacing: '0.05em' }}>
            Check page
          </span>
          <button
            type="button"
            onClick={() => setShowSettings(s => !s)}
            title="Crawl settings"
            style={{
              background: showSettings ? 'rgba(230,57,70,0.12)' : 'transparent',
              border: `1px solid ${showSettings ? 'rgba(230,57,70,0.4)' : '#2a2a2a'}`,
              borderRadius: '6px', padding: '4px 8px', cursor: 'pointer', color: showSettings ? '#e63946' : '#606060',
              fontSize: '14px', lineHeight: 1, transition: 'all 0.15s',
            }}
          >⚙</button>
          <button
            type="button"
            onClick={() => setGeoMode(g => !g)}
            title="GEO Analysis — AI Visibility"
            style={{
              background: geoMode ? 'rgba(230,57,70,0.12)' : 'transparent',
              border: `1px solid ${geoMode ? 'rgba(230,57,70,0.4)' : '#2a2a2a'}`,
              borderRadius: '6px', padding: '4px 8px', cursor: 'pointer',
              color: geoMode ? '#e63946' : '#606060',
              fontSize: '11px', fontWeight: 700, letterSpacing: '0.04em',
              lineHeight: 1, transition: 'all 0.15s',
            }}
          >GEO</button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', position: 'relative' }}>
          <span style={{ fontSize: '12px', color: limitReached ? '#e63946' : '#a0a0a0' }}>
            You have{' '}
            <span style={{ fontWeight: 700, color: '#e63946' }}>
              {checksLeft} of {DAILY_LIMIT}
            </span>{' '}
            checks left (demo)
          </span>
          <span
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
            style={{
              width: '16px', height: '16px', borderRadius: '50%', background: '#222', border: '1px solid #333',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '10px', color: '#606060', cursor: 'default', fontWeight: 700, flexShrink: 0,
            }}
          >?</span>
          {showTooltip && (
            <div style={{
              position: 'absolute', right: 0, top: '24px', zIndex: 100,
              background: '#1e1e1e', border: '1px solid #333', borderRadius: '8px',
              padding: '10px 14px', width: '220px', fontSize: '12px', color: '#a0a0a0', lineHeight: 1.5,
              boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
            }}>
              Number of free SEO checks available per day. Resets at midnight.
            </div>
          )}
        </div>
      </div>

      {showSettings && (
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #2a2a2a', background: '#0f0f0f' }}>
          <div style={{ fontSize: '10px', color: '#555', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '10px' }}>CRAWL MODE</div>
          <div style={{ display: 'flex', gap: '8px' }}>
            {[
              { val: 'standard', label: 'Standard crawl', desc: 'Fetches raw HTML' },
              { val: 'javascript', label: 'JavaScript rendering', desc: 'Renders JS content' },
            ].map(opt => (
              <button
                key={opt.val}
                type="button"
                onClick={() => setCrawlMode(opt.val)}
                style={{
                  flex: 1, background: crawlMode === opt.val ? 'rgba(230,57,70,0.1)' : '#161616',
                  border: `1px solid ${crawlMode === opt.val ? 'rgba(230,57,70,0.4)' : '#2a2a2a'}`,
                  borderRadius: '8px', padding: '10px 12px', cursor: 'pointer', textAlign: 'left', transition: 'all 0.15s',
                }}
              >
                <div style={{ fontSize: '12px', fontWeight: 700, color: crawlMode === opt.val ? '#e63946' : '#ccc', marginBottom: '2px' }}>{opt.label}</div>
                <div style={{ fontSize: '11px', color: '#555' }}>{opt.desc}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      <div style={{ padding: '24px 28px 28px' }}>
        {limitReached && (
          <div
            style={{
              background: 'rgba(230,57,70,0.08)',
              border: '1px solid rgba(230,57,70,0.25)',
              borderRadius: '8px',
              padding: '12px 16px',
              marginBottom: '16px',
              fontSize: '13px',
              color: '#e63946',
            }}
          >
            Demo limit of {DAILY_LIMIT} checks reached. Contact us to request access!
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
              style={{
                ...inputStyle,
                borderColor: focusedUrl ? '#e63946' : '#2a2a2a',
              }}
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
              style={{
                ...inputStyle,
                borderColor: focusedKw ? '#e63946' : '#2a2a2a',
              }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <button
              type="submit"
              onClick={handleAnalyze}
              disabled={loading || !url.trim() || limitReached}
              style={{
                background: loading ? '#7a1920' : limitReached ? '#333' : '#e63946',
                color: limitReached ? '#666' : '#fff',
                border: 'none',
                borderRadius: '8px',
                padding: '13px',
                fontWeight: 700,
                fontSize: '13px',
                letterSpacing: '0.06em',
                cursor: loading || !url.trim() || limitReached ? 'not-allowed' : 'pointer',
                transition: 'background 0.15s',
                opacity: !url.trim() ? 0.5 : 1,
              }}
              onMouseEnter={(e) => { if (!loading && url.trim() && !limitReached) e.target.style.background = '#ff4d5a' }}
              onMouseLeave={(e) => { if (!loading && !limitReached) e.target.style.background = '#e63946' }}
            >
              {loading ? '⏳ ANALYZING...' : '🔍 ANALYZE SEO'}
            </button>

            <button
              type="button"
              onClick={handleCompetitors}
              disabled={loading || !url.trim() || limitReached}
              style={{
                background: 'transparent',
                color: limitReached ? '#444' : '#e63946',
                border: `1px solid ${limitReached ? '#333' : 'rgba(230,57,70,0.4)'}`,
                borderRadius: '8px',
                padding: '13px',
                fontWeight: 700,
                fontSize: '13px',
                letterSpacing: '0.06em',
                cursor: loading || !url.trim() || limitReached ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s',
                opacity: !url.trim() ? 0.5 : 1,
              }}
              onMouseEnter={(e) => {
                if (!loading && url.trim() && !limitReached) {
                  e.target.style.background = 'rgba(230,57,70,0.1)'
                  e.target.style.borderColor = '#e63946'
                }
              }}
              onMouseLeave={(e) => {
                if (!loading && !limitReached) {
                  e.target.style.background = 'transparent'
                  e.target.style.borderColor = 'rgba(230,57,70,0.4)'
                }
              }}
            >
              {loading ? '⏳ LOADING...' : '🏆 FIND COMPETITORS'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
