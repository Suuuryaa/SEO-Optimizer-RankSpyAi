const CONTENT = {
  'Terms of Service': `
**Effective date:** September 2026

## Acceptance of Terms
By using RankSpy AI ("the Service"), you agree to these Terms of Service. If you do not agree, do not use the Service.

## Use of the Service
RankSpy AI provides free SEO analysis tools. You may use the Service for personal or commercial purposes, provided you do not:
- Attempt to reverse engineer, scrape, or abuse the platform
- Use automated bots to bypass rate limits
- Submit malicious URLs intended to disrupt service

## Disclaimers
The Service is provided "as is" without warranties of any kind. SEO analysis results are estimates and do not guarantee search engine rankings. We are not affiliated with Google, Bing, or any other search engine.

## Limitation of Liability
RankSpy AI shall not be liable for any indirect, incidental, or consequential damages arising from use of the Service.

## Rate Limits
Free usage is limited to 3 checks per day per device. Limits may change without notice.

## Changes
We reserve the right to modify these terms at any time. Continued use of the Service constitutes acceptance of updated terms.

## Contact
For questions, contact us through the website.
  `,
  'Privacy Policy': `
**Effective date:** September 2026

## What We Collect
- **URLs you submit** for analysis (processed in real-time, not permanently stored)
- **Usage data** via anonymous analytics (page views, feature usage)
- **Local storage** on your device to track daily check counts (never sent to our servers)

## What We Don't Collect
- No account registration required — we collect no personal information
- No cookies for tracking or advertising
- No email addresses unless you contact us directly

## Third-Party Services
We use the following third-party APIs to deliver results:
- Google PageSpeed API (subject to Google's Privacy Policy)
- Serper.dev for competitor search data
- Google Gemini for AI summaries

## Data Retention
URL submissions are processed and discarded. We do not build a database of analyzed pages.

## Your Rights
Since we collect no personal data, there is nothing to access, correct, or delete. Usage analytics are anonymous and cannot be tied to individuals.

## Contact
For privacy questions, contact us through the website.
  `,
  'Cookie Policy': `
**Effective date:** September 2026

## Cookies We Use
RankSpy AI uses **localStorage** (not traditional cookies) solely to store your daily check count so the limit resets correctly at midnight. This data:
- Never leaves your device
- Is not accessible to our servers
- Can be cleared by clearing your browser's local storage

## Analytics
We may use privacy-respecting analytics tools that do not use cookies or track individuals across sites.

## No Advertising Cookies
We do not use advertising, retargeting, or tracking cookies of any kind.

## Third-Party Cookies
Embedded third-party services (e.g. Google APIs called server-side) may set cookies per their own policies. We minimize third-party embeds to protect your privacy.

## Contact
For cookie-related questions, contact us through the website.
  `,
}

export default function LegalModal({ page, onClose }) {
  const content = CONTENT[page] || ''

  function parseMarkdown(text) {
    return text.trim().split('\n').map((line, i) => {
      if (line.startsWith('## ')) return <h3 key={i} style={{ fontSize: '14px', fontWeight: 700, color: '#fff', margin: '20px 0 8px' }}>{line.slice(3)}</h3>
      if (line.startsWith('**') && line.endsWith('**')) return <p key={i} style={{ fontSize: '12px', color: '#555', marginBottom: '4px' }}>{line.replace(/\*\*/g, '')}</p>
      if (line.startsWith('- ')) return <li key={i} style={{ fontSize: '13px', color: '#a0a0a0', marginLeft: '16px', marginBottom: '4px' }}>{line.slice(2)}</li>
      if (line.trim() === '') return <div key={i} style={{ height: '4px' }} />
      return <p key={i} style={{ fontSize: '13px', color: '#a0a0a0', lineHeight: 1.6, marginBottom: '4px' }}>{line}</p>
    })
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '24px',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#111', border: '1px solid #2a2a2a', borderRadius: '14px',
          width: '100%', maxWidth: '600px', maxHeight: '80vh',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{ padding: '18px 24px', borderBottom: '1px solid #1e1e1e', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
          <span style={{ fontSize: '15px', fontWeight: 700, color: '#fff' }}>{page}</span>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#555', fontSize: '20px', cursor: 'pointer', lineHeight: 1, padding: '0 4px' }}
          >×</button>
        </div>
        {/* Body */}
        <div style={{ padding: '20px 24px', overflowY: 'auto' }}>
          {parseMarkdown(content)}
        </div>
      </div>
    </div>
  )
}
