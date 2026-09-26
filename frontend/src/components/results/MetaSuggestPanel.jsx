import { useState } from 'react'
import { suggestMeta } from '../../api'

function CopyBtn({ text }) {
  const [copied, setCopied] = useState(false)
  function copy() {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }
  return (
    <button
      onClick={copy}
      style={{
        background: copied ? 'rgba(34,197,94,0.1)' : '#1a1a1a',
        border: `1px solid ${copied ? 'rgba(34,197,94,0.3)' : '#2a2a2a'}`,
        borderRadius: '6px', padding: '4px 10px', cursor: 'pointer',
        fontSize: '11px', fontWeight: 700, color: copied ? '#22c55e' : '#606060',
        transition: 'all 0.2s',
      }}
    >
      {copied ? '✓ Copied' : 'Copy'}
    </button>
  )
}

export default function MetaSuggestPanel({ url, keyword, currentTitle, currentMeta }) {
  const [state, setState] = useState('idle') // idle | loading | done | error
  const [result, setResult] = useState(null)
  const [error, setError]   = useState(null)

  async function handleGenerate() {
    setState('loading')
    setError(null)
    try {
      const data = await suggestMeta({ url, keyword })
      setResult(data)
      setState('done')
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Failed')
      setState('error')
    }
  }

  return (
    <div style={{ background: '#111', border: '1px solid #222', borderRadius: '12px', overflow: 'hidden', marginTop: '8px' }}>
      {/* Header */}
      <div style={{
        background: '#161616', padding: '14px 20px', borderBottom: '1px solid #1e1e1e',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>AI Meta Tag Generator</span>
          <span style={{ fontSize: '11px', color: '#555', marginLeft: '8px' }}>BART + rule-based</span>
        </div>
        {state !== 'done' && (
          <button
            onClick={handleGenerate}
            disabled={state === 'loading'}
            style={{
              background: state === 'loading' ? '#1a1a1a' : '#e63946',
              color: state === 'loading' ? '#555' : '#fff',
              border: 'none', borderRadius: '7px', padding: '8px 16px',
              fontWeight: 700, fontSize: '12px', cursor: state === 'loading' ? 'not-allowed' : 'pointer',
              letterSpacing: '0.04em',
            }}
          >
            {state === 'loading' ? '⏳ Generating…' : '✨ Generate Suggestions'}
          </button>
        )}
      </div>

      <div style={{ padding: '20px' }}>
        {state === 'idle' && (
          <div style={{ fontSize: '13px', color: '#555', textAlign: 'center', padding: '16px 0' }}>
            Click "Generate Suggestions" to get AI-powered meta title and description
            optimised for <span style={{ color: '#e63946' }}>"{keyword || 'your keyword'}"</span>
          </div>
        )}

        {state === 'error' && (
          <div style={{ fontSize: '13px', color: '#e63946', background: 'rgba(230,57,70,0.08)', border: '1px solid rgba(230,57,70,0.2)', borderRadius: '8px', padding: '12px 16px' }}>
            Error: {error}
          </div>
        )}

        {state === 'done' && result && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

            {/* Suggested title */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '11px', color: '#555', fontWeight: 700, letterSpacing: '0.08em' }}>SUGGESTED TITLE</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '11px', color: result.suggested_title.length <= 60 ? '#22c55e' : '#e63946' }}>
                    {result.suggested_title.length}/60 chars
                  </span>
                  <CopyBtn text={result.suggested_title} />
                </div>
              </div>
              <div style={{ background: '#0e0e0e', border: '1px solid #1e1e1e', borderRadius: '8px', padding: '12px 14px', fontSize: '13px', color: '#e0e0e0', lineHeight: 1.5 }}>
                {result.suggested_title}
              </div>
              {result.title_changes?.length > 0 && (
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '6px' }}>
                  {result.title_changes.map((c, i) => (
                    <span key={i} style={{ fontSize: '10px', background: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.2)', color: '#22c55e', padding: '2px 8px', borderRadius: '4px' }}>{c}</span>
                  ))}
                </div>
              )}
            </div>

            {/* Suggested meta */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '11px', color: '#555', fontWeight: 700, letterSpacing: '0.08em' }}>SUGGESTED META DESCRIPTION</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '11px', color: result.suggested_meta.length <= 160 ? '#22c55e' : '#e63946' }}>
                    {result.suggested_meta.length}/160 chars
                  </span>
                  <CopyBtn text={result.suggested_meta} />
                </div>
              </div>
              <div style={{ background: '#0e0e0e', border: '1px solid #1e1e1e', borderRadius: '8px', padding: '12px 14px', fontSize: '13px', color: '#e0e0e0', lineHeight: 1.6 }}>
                {result.suggested_meta}
              </div>
              {result.meta_changes?.length > 0 && (
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '6px' }}>
                  {result.meta_changes.map((c, i) => (
                    <span key={i} style={{ fontSize: '10px', background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)', color: '#3b82f6', padding: '2px 8px', borderRadius: '4px' }}>{c}</span>
                  ))}
                </div>
              )}
            </div>

            {/* Regenerate */}
            <button
              onClick={handleGenerate}
              style={{ background: 'transparent', border: '1px solid #2a2a2a', borderRadius: '7px', padding: '8px 14px', color: '#606060', fontSize: '12px', cursor: 'pointer', alignSelf: 'flex-start' }}
            >
              ↺ Regenerate
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
