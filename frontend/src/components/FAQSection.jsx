import { useId, useState } from 'react'

import { HOME_FAQ } from '../faqData'

export function FAQItem({ q, a }) {
  const [open, setOpen] = useState(false)
  const id = useId()

  return (
    <div
      style={{
        borderBottom: '1px solid #1a1a1a',
      }}
    >
      <h3 style={{ margin: 0 }}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={`${id}-a`}
        id={`${id}-q`}
        onClick={() => setOpen((o) => !o)}
        style={{
          width: '100%',
          background: 'none',
          border: 'none',
          padding: '20px 0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <span style={{ fontSize: '14px', fontWeight: 600, color: '#e0e0e0', lineHeight: '1.4', fontFamily: 'inherit' }}>{q}</span>
        <span
          aria-hidden="true"
          style={{
            flexShrink: 0,
            width: '24px',
            height: '24px',
            borderRadius: '50%',
            background: open ? 'rgba(230,57,70,0.15)' : '#1a1a1a',
            border: open ? '1px solid rgba(230,57,70,0.4)' : '1px solid #2a2a2a',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '16px',
            color: open ? '#ff6b75' : '#a0a0a0',
            transition: 'all 0.2s',
            lineHeight: 1,
          }}
        >
          {open ? '−' : '+'}
        </span>
      </button>
      </h3>

      {open && (
        <div
          id={`${id}-a`}
          role="region"
          aria-labelledby={`${id}-q`}
          style={{
            paddingBottom: '20px',
            fontSize: '13px',
            color: '#a0a0a0',
            lineHeight: '1.7',
          }}
        >
          {a}
        </div>
      )}
    </div>
  )
}

export default function FAQSection() {
  return (
    <div style={{ padding: '48px 0' }}>
      <div style={{ maxWidth: '1088px', margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: '48px' }}>
          <h2
            style={{
              fontSize: '28px',
              fontWeight: 800,
              color: '#fff',
              letterSpacing: '-0.5px',
            }}
          >
            Frequently Asked Questions
          </h2>
        </div>

        <div
          style={{
            background: '#111',
            border: '1px solid #1f1f1f',
            borderRadius: '14px',
            padding: '0 20px',
          }}
        >
          {HOME_FAQ.map((item) => (
            <FAQItem key={item.q} q={item.q} a={item.a} />
          ))}
        </div>
        <p style={{ textAlign: 'center', margin: '20px 0 0' }}>
          <a href="/faq" style={{ color: '#ff8a92', fontWeight: 700, fontSize: '14px', textDecoration: 'none' }}>
            See all questions &rarr;
          </a>
        </p>
      </div>
    </div>
  )
}
