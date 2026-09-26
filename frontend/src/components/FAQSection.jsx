import { useState } from 'react'

const FAQS = [
  {
    q: 'What does RankSpy AI analyze?',
    a: 'RankSpy AI crawls your URL like a search engine and checks 200+ SEO factors including meta tags, content quality, page speed, link structure, technical configuration, and AI/GEO signals.',
  },
  {
    q: 'Is it really free?',
    a: 'Yes — the core SEO analysis and competitor finder are completely free with no sign-up required. You get real results instantly.',
  },
  {
    q: 'What is the SEO score?',
    a: 'The SEO score (0–100) reflects how well your page is optimized. Scores above 70 indicate a strong foundation, 40–69 needs optimization, and below 40 means critical issues need fixing immediately.',
  },
  {
    q: 'How does the competitor finder work?',
    a: 'Enter your URL and keyword, and we search the web for direct competitors ranking for that keyword. We then analyze each competitor\'s SEO so you can see exactly where you stand.',
  },
  {
    q: 'How do I improve my score?',
    a: 'After analysis, you\'ll receive a prioritized list of recommendations sorted by impact — Critical, High, and Medium priority. Work through them top to bottom.',
  },
  {
    q: 'Does it work for any website?',
    a: 'Yes — any publicly accessible URL works. It\'s especially useful for business websites, blogs, e-commerce stores, and landing pages.',
  },
  {
    q: 'What are GEO / AI signals?',
    a: 'GEO (Generative Engine Optimization) checks how visible your site is to AI tools like ChatGPT and Perplexity. We check AI crawler access, LLMs.txt files, and E-E-A-T signals.',
  },
]

function FAQItem({ q, a }) {
  const [open, setOpen] = useState(false)

  return (
    <div
      style={{
        borderBottom: '1px solid #1a1a1a',
      }}
    >
      <button
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
        <span style={{ fontSize: '14px', fontWeight: 600, color: '#e0e0e0', lineHeight: '1.4' }}>{q}</span>
        <span
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
            color: open ? '#e63946' : '#606060',
            transition: 'all 0.2s',
            lineHeight: 1,
          }}
        >
          {open ? '−' : '+'}
        </span>
      </button>

      {open && (
        <div
          style={{
            paddingBottom: '20px',
            fontSize: '13px',
            color: '#808080',
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
    <div style={{ padding: '80px 24px' }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
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
            padding: '0 28px',
          }}
        >
          {FAQS.map((item) => (
            <FAQItem key={item.q} q={item.q} a={item.a} />
          ))}
        </div>
      </div>
    </div>
  )
}
