import { useState } from 'react'
import { generateSchema } from '../../api'

export default function SchemaPanel({ url, keyword }) {
  const [state, setState] = useState('idle')
  const [result, setResult] = useState(null)
  const [error, setError]   = useState(null)
  const [copied, setCopied] = useState(false)

  async function handleGenerate() {
    setState('loading')
    setError(null)
    try {
      const data = await generateSchema({ url, keyword })
      setResult(data)
      setState('done')
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Failed')
      setState('error')
    }
  }

  function copySchema() {
    if (!result?.schema_html) return
    navigator.clipboard.writeText(result.schema_html).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    })
  }

  const typeColors = {
    FAQPage: '#a855f7', Product: '#f97316', LocalBusiness: '#22c55e',
    Article: '#3b82f6', WebPage: '#e63946', WebSite: '#eab308',
  }

  return (
    <div style={{ background: '#111', border: '1px solid #222', borderRadius: '12px', overflow: 'hidden', marginTop: '8px' }}>
      <div style={{
        background: '#161616', padding: '14px 20px', borderBottom: '1px solid #1e1e1e',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div>
          <span style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>Schema Markup Generator</span>
          <span style={{ fontSize: '11px', color: '#555', marginLeft: '8px' }}>JSON-LD structured data</span>
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
            }}
          >
            {state === 'loading' ? '⏳ Generating…' : '🔧 Generate Schema'}
          </button>
        )}
      </div>

      <div style={{ padding: '20px' }}>
        {state === 'idle' && (
          <div style={{ fontSize: '13px', color: '#555', textAlign: 'center', padding: '16px 0' }}>
            Auto-detects page type and generates ready-to-paste JSON-LD structured data.<br />
            Supports: FAQPage, Product, Article, LocalBusiness, WebPage.
          </div>
        )}

        {state === 'error' && (
          <div style={{ fontSize: '13px', color: '#e63946', background: 'rgba(230,57,70,0.08)', border: '1px solid rgba(230,57,70,0.2)', borderRadius: '8px', padding: '12px 16px' }}>
            Error: {error}
          </div>
        )}

        {state === 'done' && result && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Detected type badge */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '12px', color: '#a0a0a0' }}>Detected page type:</span>
              <span style={{
                fontSize: '12px', fontWeight: 800, padding: '3px 12px', borderRadius: '99px',
                background: `${typeColors[result.page_type] || '#e63946'}18`,
                border: `1px solid ${typeColors[result.page_type] || '#e63946'}40`,
                color: typeColors[result.page_type] || '#e63946',
              }}>
                {result.page_type}
              </span>
              <span style={{ fontSize: '12px', color: '#555' }}>{result.count} schema block{result.count !== 1 ? 's' : ''}</span>
            </div>

            {/* Schema code block */}
            <div style={{ position: 'relative' }}>
              <pre style={{
                background: '#0a0a0a', border: '1px solid #1e1e1e', borderRadius: '8px',
                padding: '16px', fontSize: '11px', color: '#a0a0a0', lineHeight: 1.6,
                overflowX: 'auto', maxHeight: '320px', overflowY: 'auto',
                fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                margin: 0,
              }}>
                {result.schema_html}
              </pre>
              <button
                onClick={copySchema}
                style={{
                  position: 'absolute', top: '10px', right: '10px',
                  background: copied ? 'rgba(34,197,94,0.15)' : 'rgba(255,255,255,0.05)',
                  border: `1px solid ${copied ? 'rgba(34,197,94,0.3)' : '#2a2a2a'}`,
                  borderRadius: '6px', padding: '5px 12px',
                  color: copied ? '#22c55e' : '#606060', fontSize: '11px', fontWeight: 700,
                  cursor: 'pointer', transition: 'all 0.2s',
                }}
              >
                {copied ? '✓ Copied!' : 'Copy all'}
              </button>
            </div>

            <div style={{ fontSize: '12px', color: '#555', background: '#0e0e0e', border: '1px solid #1a1a1a', borderRadius: '8px', padding: '12px 14px' }}>
              <span style={{ fontWeight: 700, color: '#444' }}>How to use:</span> Paste this code inside the <code style={{ color: '#e63946' }}>&lt;head&gt;</code> section of your HTML. Replace any <code style={{ color: '#eab308' }}>{"<!-- placeholder -->"}</code> comments with your actual data.
            </div>

            <button onClick={handleGenerate} style={{ background: 'transparent', border: '1px solid #2a2a2a', borderRadius: '7px', padding: '8px 14px', color: '#606060', fontSize: '12px', cursor: 'pointer', alignSelf: 'flex-start' }}>
              ↺ Regenerate
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
