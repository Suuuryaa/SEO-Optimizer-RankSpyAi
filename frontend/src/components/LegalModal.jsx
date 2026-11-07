import Modal from './ui/Modal'

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
Free usage draws from a shared daily pool of checks, plus per-IP daily caps on some features. Limits may change without notice.

## Changes
We reserve the right to modify these terms at any time. Continued use of the Service constitutes acceptance of updated terms.

## Contact
For questions, contact us through the website.
  `,
  'Privacy Policy': `
**Effective date:** September 2026

## What We Collect
- **URLs and keywords you submit** for analysis. Results may be cached for up to 24 hours to speed up repeat checks.
- **Your IP address**, held temporarily (up to 25 hours) to enforce daily usage limits and prevent abuse.
- **URLs and keywords you choose to track** with the rank tracker, stored with their ranking history until removed.

## What We Don't Collect
- No account registration required
- No cookies for tracking or advertising
- No email addresses unless you contact us directly

## Third-Party Services
We use the following third-party APIs to deliver results:
- Google PageSpeed API (subject to Google's Privacy Policy)
- Serper.dev for competitor search data
- Google Gemini for AI summaries

## Data Retention
Cached analysis results expire after 24 hours. Rate-limit counters expire after 25 hours. Tracked keywords are kept until you ask us to remove them.

## Your Rights
You can ask us to delete tracked keywords or a contact message you sent by contacting us through the website.

## Contact
For privacy questions, contact us through the website.
  `,
  'Cookie Policy': `
**Effective date:** September 2026

## Cookies We Use
RankSpy AI does not set cookies. Daily usage limits are counted on our server, not in your browser.

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

function parseMarkdown(text) {
  return text.trim().split('\n').map((line, i) => {
    if (line.startsWith('## ')) return <h3 key={i} style={{ fontSize: '14px', fontWeight: 700, color: '#fff', margin: '20px 0 8px' }}>{line.slice(3)}</h3>
    if (line.startsWith('**') && line.endsWith('**')) return <p key={i} style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>{line.replace(/\*\*/g, '')}</p>
    if (line.startsWith('- ')) return <li key={i} style={{ fontSize: '13px', color: 'var(--text-body)', marginLeft: '16px', marginBottom: '4px' }}>{line.slice(2).replace(/\*\*/g, '')}</li>
    if (line.trim() === '') return <div key={i} style={{ height: '4px' }} />
    return <p key={i} style={{ fontSize: '13px', color: 'var(--text-body)', lineHeight: 1.6, marginBottom: '4px' }}>{line}</p>
  })
}

export default function LegalModal({ page, onClose }) {
  return (
    <Modal title={page} onClose={onClose}>
      {parseMarkdown(CONTENT[page] || '')}
    </Modal>
  )
}
