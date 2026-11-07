import { useState } from 'react'

// "Text in images": words baked into the page's main pictures, read by two
// engines (RapidOCR on our server + Gemini). Findings also appear in the to-do list.

const SOURCE = {
  both: { label: 'Both readers agree', color: '#4ade80', bg: 'rgba(74,222,128,0.1)', border: 'rgba(74,222,128,0.3)' },
  both_differ: { label: 'Readers differ · Gemini used', color: '#f5b041', bg: 'rgba(245,176,65,0.1)', border: 'rgba(245,176,65,0.3)' },
  gemini: { label: 'Gemini only', color: '#c0c0c0', bg: '#1a1a1a', border: '#2a2a2a' },
  ocr: { label: 'RapidOCR only', color: '#c0c0c0', bg: '#1a1a1a', border: '#2a2a2a' },
}

const ISSUE = {
  text_without_alt: 'Words in this image have no alt text',
  alt_does_not_match: "Alt text doesn't mention any of the words shown",
  phone_only_in_image: 'Phone number only shown in this image',
}

const ENGINE_LABEL = {
  ok: null,
  no_key: 'not set up',
  quota: 'daily limit reached',
  timeout: 'too slow, skipped',
  unavailable: 'not installed',
  bad_response: "couldn't read its answer",
  invalid_key: 'key not accepted',
  all_failed: 'unavailable',
}

function Chip({ s }) {
  const t = SOURCE[s]
  if (!t) return null
  return (
    <span style={{ background: t.bg, border: `1px solid ${t.border}`, color: t.color, borderRadius: '4px', padding: '2px 7px', fontSize: '11px', fontWeight: 600, whiteSpace: 'nowrap' }}>
      {t.label}
    </span>
  )
}

function ImageRow({ img }) {
  const lines = String(img.text || '').split(' | ').filter(Boolean)
  return (
    <li style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 120px) 1fr', gap: '14px', padding: '14px 0', borderTop: '1px solid #1e1e1e' }}>
      <a href={img.url} target="_blank" rel="noopener noreferrer" style={{ display: 'block' }} aria-label="Open image in a new tab">
        <img
          src={img.url} alt="" loading="lazy" referrerPolicy="no-referrer"
          style={{ width: '100%', aspectRatio: '4 / 3', objectFit: 'cover', borderRadius: '8px', background: '#1a1a1a', border: '1px solid #232323' }}
          onError={e => { e.currentTarget.style.visibility = 'hidden' }}
        />
      </a>
      <div style={{ minWidth: 0 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center', marginBottom: '6px' }}>
          <Chip s={img.source} />
          {img.keyword_found && (
            <span style={{ fontSize: '11px', fontWeight: 700, color: '#ff8a93' }}>Contains your keyword</span>
          )}
          {img.description && <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{img.description}</span>}
        </div>
        <div style={{ fontSize: '13px', color: '#e6e6e6', lineHeight: 1.5, wordBreak: 'break-word' }}>
          {lines.slice(0, 6).map((l, i) => <div key={i}>&ldquo;{l}&rdquo;</div>)}
          {lines.length > 6 && <div style={{ color: 'var(--text-muted)', fontSize: '12px' }}>+{lines.length - 6} more lines</div>}
        </div>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px' }}>
          Alt text: {img.alt ? <span style={{ color: '#cfcfcf' }}>&ldquo;{img.alt}&rdquo;</span> : <span style={{ color: '#ff8a93' }}>none</span>}
        </div>
        {img.issues?.length > 0 && (
          <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0', display: 'grid', gap: '4px' }}>
            {img.issues.map(k => (
              <li key={k} style={{ fontSize: '12px', color: '#f5b041' }}>⚠ {ISSUE[k] || k}</li>
            ))}
            {img.suggested_alt && img.issues.some(k => k !== 'phone_only_in_image') && (
              <li style={{ fontSize: '12px', color: '#cfcfcf' }}>
                Suggested alt: <code style={{ background: '#1a1a1a', padding: '1px 6px', borderRadius: '4px', color: '#fff' }}>{img.suggested_alt}</code>
              </li>
            )}
          </ul>
        )}
      </div>
    </li>
  )
}

export default function ImageTextPanel({ data }) {
  const [showAll, setShowAll] = useState(false)
  if (!data) return null
  if (data.error) {
    return (
      <div style={{ background: '#111', border: '1px solid #222', borderRadius: '12px', padding: '16px 20px', fontSize: '13px', color: 'var(--text-body)' }}>
        The text-in-images check isn&rsquo;t available right now. The rest of your results are unaffected.
      </div>
    )
  }

  const withText = (data.images || []).filter(i => i.word_count > 0)
  const noText = (data.images || []).length - withText.length
  const shown = showAll ? withText : withText.slice(0, 3)
  const engineNotes = Object.entries(data.engines || {})
    .filter(([, v]) => v !== 'ok')
    .map(([k, v]) => `${k === 'rapidocr' ? 'RapidOCR' : 'Gemini'}: ${ENGINE_LABEL[v] || 'unavailable'}`)

  return (
    <section aria-labelledby="imgtext-h" style={{ background: '#111', border: '1px solid #222', borderRadius: '12px', padding: '20px' }}>
      <h2 id="imgtext-h" style={{ fontSize: '16px', color: '#fff', fontWeight: 800, margin: 0 }}>Text in images</h2>
      <p style={{ fontSize: '13px', color: 'var(--text-body)', margin: '6px 0 0', lineHeight: 1.5 }}>
        Words inside pictures are hard for Google and AI search to read. We read your page&rsquo;s main images with two
        readers and compare them.
      </p>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 20px', fontSize: '13px', color: '#cfcfcf', marginTop: '14px' }}>
        <span><b style={{ color: '#fff' }}>{data.checked}</b> images read</span>
        <span><b style={{ color: '#fff' }}>{data.with_text}</b> contain words</span>
        {engineNotes.length > 0 && <span style={{ color: '#f5b041' }}>{engineNotes.join(' · ')}</span>}
      </div>

      {data.keyword_only_in_images && (
        <div role="alert" style={{ marginTop: '14px', background: 'rgba(230,57,70,0.08)', border: '1px solid rgba(230,57,70,0.35)', borderRadius: '10px', padding: '12px 14px', fontSize: '13px', color: '#ffb3b8' }}>
          Your keyword appears <b>only inside an image</b>. Add it to your H1 heading and first paragraph as real text.
        </div>
      )}
      {data.phones_only_in_images?.length > 0 && (
        <div style={{ marginTop: '10px', background: 'rgba(245,176,65,0.08)', border: '1px solid rgba(245,176,65,0.3)', borderRadius: '10px', padding: '12px 14px', fontSize: '13px', color: '#f5d08a' }}>
          Phone number {data.phones_only_in_images[0]} is only shown in an image. Add it as text with a tap-to-call link.
        </div>
      )}

      {data.checked === 0 ? (
        <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '14px 0 0' }}>{data.note || 'No images to read on this page.'}</p>
      ) : withText.length === 0 ? (
        <p style={{ fontSize: '13px', color: '#4ade80', margin: '14px 0 0' }}>✓ None of the main images rely on words. Nothing to fix here.</p>
      ) : (
        <>
          <ul style={{ listStyle: 'none', padding: 0, margin: '14px 0 0' }}>
            {shown.map(img => <ImageRow key={img.url} img={img} />)}
          </ul>
          {withText.length > 3 && (
            <button type="button" onClick={() => setShowAll(v => !v)}
              style={{ background: 'none', border: '1px solid #2a2a2a', borderRadius: '6px', color: 'var(--text-body)', fontSize: '12px', padding: '6px 12px', cursor: 'pointer', marginTop: '6px' }}>
              {showAll ? 'Show fewer' : `Show all ${withText.length} images with words`}
            </button>
          )}
          {noText > 0 && (
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '10px 0 0' }}>
              {noText} more image{noText > 1 ? 's' : ''} had no words.
            </p>
          )}
        </>
      )}
    </section>
  )
}
