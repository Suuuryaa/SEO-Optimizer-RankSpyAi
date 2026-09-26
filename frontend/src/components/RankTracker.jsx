import { useState, useEffect } from 'react'
import { trackKeyword, getRankings } from '../api'

export default function RankTracker({ url, keyword }) {
  const [status, setStatus] = useState('idle')   // idle | loading | tracked | error
  const [history, setHistory] = useState([])
  const [errorMsg, setErrorMsg] = useState('')

  // Load existing rankings on mount
  useEffect(() => {
    if (!url) return
    getRankings(url)
      .then(res => {
        const entry = (res.tracked || []).find(
          t => t.keyword?.toLowerCase() === keyword?.toLowerCase()
        )
        if (entry) {
          setStatus('tracked')
          const sorted = [...(entry.rank_history || [])].sort(
            (a, b) => new Date(b.checked_at) - new Date(a.checked_at)
          )
          setHistory(sorted)
        }
      })
      .catch(() => {/* silently ignore on load */})
  }, [url, keyword])

  async function handleTrack() {
    setStatus('loading')
    setErrorMsg('')
    try {
      const res = await trackKeyword({ url, keyword })
      setStatus('tracked')
      // Append the fresh rank check to history if present
      if (res.rank && !res.rank.error) {
        setHistory(prev => [
          {
            position: res.rank.position,
            found: res.rank.found,
            checked_at: res.rank.checked_at,
          },
          ...prev,
        ])
      }
    } catch (err) {
      setStatus('error')
      setErrorMsg(err?.response?.data?.detail || 'Something went wrong. Try again.')
    }
  }

  function positionColor(pos, found) {
    if (!found || pos == null) return '#e63946'
    if (pos <= 10) return '#22c55e'
    if (pos <= 30) return '#f97316'
    return '#e63946'
  }

  function formatDate(iso) {
    try {
      return new Date(iso).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
      })
    } catch {
      return iso
    }
  }

  return (
    <div style={{
      background: '#111',
      border: '1px solid #222',
      borderRadius: '12px',
      overflow: 'hidden',
      marginTop: '8px',
    }}>
      {/* Header */}
      <div style={{
        background: '#161616',
        padding: '13px 20px',
        borderBottom: '1px solid #222',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '10px',
      }}>
        <div>
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>
            Keyword Rank Tracker
          </span>
          <span style={{
            fontSize: '11px',
            color: '#555',
            marginLeft: '10px',
          }}>
            Track "{keyword}" on Google
          </span>
        </div>

        {status !== 'tracked' && (
          <button
            onClick={handleTrack}
            disabled={status === 'loading'}
            style={{
              background: status === 'loading' ? '#1e1e1e' : '#e63946',
              color: status === 'loading' ? '#555' : '#fff',
              border: 'none',
              borderRadius: '8px',
              padding: '8px 18px',
              fontSize: '12px',
              fontWeight: 700,
              cursor: status === 'loading' ? 'not-allowed' : 'pointer',
              transition: 'background 0.2s',
              letterSpacing: '0.02em',
            }}
          >
            {status === 'loading' ? 'Checking...' : 'Track this keyword'}
          </button>
        )}
      </div>

      {/* Body */}
      <div style={{ padding: '18px 20px' }}>

        {/* Error */}
        {status === 'error' && (
          <div style={{
            fontSize: '13px',
            color: '#e63946',
            background: 'rgba(230,57,70,0.08)',
            border: '1px solid rgba(230,57,70,0.2)',
            borderRadius: '8px',
            padding: '10px 14px',
            marginBottom: '12px',
          }}>
            {errorMsg}
          </div>
        )}

        {/* Idle prompt */}
        {status === 'idle' && (
          <p style={{ fontSize: '13px', color: '#555', margin: 0 }}>
            Click "Track this keyword" to start monitoring your SERP position daily.
          </p>
        )}

        {/* Tracking confirmed */}
        {(status === 'tracked' || history.length > 0) && (
          <div style={{ marginBottom: history.length > 0 ? '16px' : 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{
                display: 'inline-block',
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#22c55e',
                flexShrink: 0,
              }} />
              <span style={{ fontSize: '13px', color: '#c8c8c8' }}>
                Tracking <strong style={{ color: '#fff' }}>"{keyword}"</strong> for{' '}
                <span style={{ color: '#a0a0a0', wordBreak: 'break-all' }}>{url}</span>
              </span>
            </div>
            <div style={{ fontSize: '11px', color: '#444', marginTop: '4px', marginLeft: '16px' }}>
              Rank checks run daily
            </div>
          </div>
        )}

        {/* History table */}
        {history.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#0e0e0e' }}>
                  {['Date', 'Position'].map(h => (
                    <th
                      key={h}
                      style={{
                        padding: '8px 14px',
                        fontSize: '10px',
                        color: '#555',
                        fontWeight: 700,
                        letterSpacing: '0.08em',
                        textAlign: 'left',
                        borderBottom: '1px solid #1e1e1e',
                        textTransform: 'uppercase',
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {history.map((row, i) => {
                  const col = positionColor(row.position, row.found)
                  return (
                    <tr key={i} style={{ borderBottom: '1px solid #181818' }}>
                      <td style={{ padding: '10px 14px', fontSize: '12px', color: '#a0a0a0' }}>
                        {formatDate(row.checked_at)}
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <span style={{
                          fontSize: '13px',
                          fontWeight: 800,
                          color: col,
                        }}>
                          {row.found && row.position != null
                            ? `#${row.position}`
                            : 'Not found'}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
