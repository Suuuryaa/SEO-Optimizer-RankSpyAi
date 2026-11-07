import { useEffect, useState } from 'react'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import LegalModal from './components/LegalModal'
import ContactModal from './components/ContactModal'
import { FAQItem } from './components/FAQSection'
import { FAQ_GROUPS } from './faqData'

// Google/AI-readable copy of the questions (FAQPage structured data)
function useFaqSchema() {
  useEffect(() => {
    const el = document.createElement('script')
    el.type = 'application/ld+json'
    el.text = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: FAQ_GROUPS.flatMap(g => g.items).map(({ q, a }) => ({
        '@type': 'Question', name: q, acceptedAnswer: { '@type': 'Answer', text: a },
      })),
    })
    document.head.appendChild(el)
    return () => el.remove()
  }, [])
}

export default function FaqPage() {
  const [legalPage, setLegalPage] = useState(null)
  const [showContact, setShowContact] = useState(false)
  useFaqSchema()

  return (
    <>
      <Navbar />
      <main id="top" style={{ paddingTop: '60px' }}>
        {/* Title */}
        <header style={{ textAlign: 'center', padding: '56px 16px 28px', maxWidth: '760px', margin: '0 auto' }}>
          <h1 style={{ fontSize: 'clamp(30px, 4.4vw, 46px)', fontWeight: 800, letterSpacing: '-0.03em', color: '#fff', margin: '0 0 12px' }}>
            Frequently asked questions
          </h1>
          <p style={{ fontSize: '16px', color: 'var(--text-body, #a0a0a0)', margin: 0, lineHeight: 1.6 }}>
            Everything about free scans, scores, competitor comparison, AI visibility and your data.
          </p>
        </header>

        {/* Topic chips */}
        <nav aria-label="FAQ topics" style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '8px', padding: '0 16px 32px', maxWidth: '820px', margin: '0 auto' }}>
          {FAQ_GROUPS.map(g => (
            <a key={g.id} href={`#${g.id}`} className="faq-chip">{g.title}</a>
          ))}
        </nav>

        {/* Questions, grouped */}
        <div style={{ maxWidth: '760px', margin: '0 auto', padding: '0 16px' }}>
          {FAQ_GROUPS.map(g => (
            <section key={g.id} id={g.id} aria-labelledby={`${g.id}-h`} style={{ marginBottom: '36px', scrollMarginTop: '80px' }}>
              <h2 id={`${g.id}-h`} style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: '#ff8a92', margin: '0 0 8px' }}>
                {g.title}
              </h2>
              <div style={{ background: '#111', border: '1px solid #1f1f1f', borderRadius: '14px', padding: '0 20px' }}>
                {g.items.map(item => <FAQItem key={item.q} q={item.q} a={item.a} />)}
              </div>
            </section>
          ))}

          <p style={{ textAlign: 'center', fontSize: '14px', color: 'var(--text-body, #a0a0a0)', margin: '8px 0 56px' }}>
            Still have a question?{' '}
            <button type="button" onClick={() => setShowContact(true)}
              style={{ background: 'none', border: 'none', padding: 0, color: '#ff8a92', fontWeight: 700, cursor: 'pointer', fontSize: '14px', fontFamily: 'inherit' }}>
              Contact us
            </button>
          </p>
        </div>

        {/* Call to action */}
        <section aria-labelledby="faq-cta-h" style={{ maxWidth: '1000px', margin: '0 auto 64px', padding: '0 16px' }}>
          <div className="faq-cta">
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: '12px', fontWeight: 700, letterSpacing: '0.1em', color: '#ff8a92', textTransform: 'uppercase', marginBottom: '10px' }}>
                Free SEO and AI-visibility check
              </div>
              <h2 id="faq-cta-h" style={{ fontSize: 'clamp(24px, 3vw, 32px)', fontWeight: 800, color: '#fff', letterSpacing: '-0.02em', lineHeight: 1.2, margin: '0 0 12px' }}>
                Find out why your page isn&rsquo;t ranking, and what to fix first
              </h2>
              <p style={{ fontSize: '15px', color: '#c8c8c8', lineHeight: 1.6, margin: '0 0 22px' }}>
                3 free scans a day. No sign-up, no card.
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                <a href="/#scan" className="faq-btn-primary">Check my page</a>
                <a href="/#how-it-works" className="faq-btn-secondary">See how it works</a>
              </div>
            </div>
            <ul className="faq-cta-list" aria-label="What you get">
              {['Score out of 100 and a to-do list', 'Real Google positions vs your rivals', 'Can ChatGPT and Perplexity read you?', 'Better title and description, written for you'].map(t => (
                <li key={t}><span aria-hidden="true" style={{ color: '#22c55e', marginRight: '8px' }}>✓</span>{t}</li>
              ))}
            </ul>
          </div>
        </section>
      </main>

      <Footer onLegal={setLegalPage} onContact={() => setShowContact(true)} />
      {legalPage && <LegalModal page={legalPage} onClose={() => setLegalPage(null)} />}
      {showContact && <ContactModal onClose={() => setShowContact(false)} />}

      <style>{`
        .faq-chip { font-size: 13px; font-weight: 600; color: #d0d0d0; text-decoration: none; padding: 7px 14px; border: 1px solid #2a2a2a; border-radius: 100px; background: #111; }
        .faq-chip:hover { color: #fff; border-color: #444; }
        .faq-cta { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr); gap: 32px; align-items: center;
          background: radial-gradient(ellipse at 0% 100%, rgba(230,57,70,0.28), transparent 60%), #140b0b;
          border: 1px solid #2a1717; border-radius: 18px; padding: 40px; }
        .faq-cta-list { list-style: none; margin: 0; padding: 20px; background: rgba(0,0,0,0.35); border: 1px solid #2a2a2a; border-radius: 12px; display: grid; gap: 12px; font-size: 14px; color: #e0e0e0; }
        .faq-btn-primary { background: #e63946; color: #fff; font-weight: 700; font-size: 14px; padding: 12px 20px; border-radius: 8px; text-decoration: none; }
        .faq-btn-secondary { background: transparent; color: #fff; font-weight: 600; font-size: 14px; padding: 12px 20px; border-radius: 8px; text-decoration: none; border: 1px solid #3a3a3a; }
        .faq-btn-secondary:hover { border-color: #666; }
        @media (max-width: 760px) { .faq-cta { grid-template-columns: minmax(0, 1fr); padding: 28px 22px; } }
      `}</style>
    </>
  )
}
