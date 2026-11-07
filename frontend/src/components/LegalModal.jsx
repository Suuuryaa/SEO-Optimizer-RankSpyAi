import Modal from './ui/Modal'

const CONTENT = {
  'Terms of Service': `
**Effective date:** 8 November 2026

## Acceptance of Terms
By using RankSpy AI ("the Service"), you agree to these Terms of Service. If you do not agree, do not use the Service.

## Use of the Service
RankSpy AI provides SEO analysis tools. You may use the Service for personal or commercial purposes, provided you do not:
- Attempt to reverse engineer, scrape, or abuse the platform
- Use automated scripts or many accounts or connections to get around usage limits
- Submit URLs you are not allowed to analyse, or URLs intended to disrupt the Service

## Free Usage Limits
Free use is limited per visitor (per internet connection): currently 3 page scans and 1 competitor comparison a day, plus free rescans of a page you have already scanned. A site-wide daily cap also applies. Limits reset at midnight UTC and may change without notice.

## Results and AI Content
Scores, Google positions and competitor data are estimates and do not guarantee rankings or traffic. Some text is written by AI and may be inaccurate. For competitor sites that block automated checks, we show data from Google's public tools instead. We are not affiliated with Google, Bing, or any other search engine.

## Disclaimers
The Service is provided "as is" without warranties of any kind.

## Limitation of Liability
RankSpy AI shall not be liable for any indirect, incidental, or consequential damages arising from use of the Service.

## Changes
We may change these terms at any time. Continued use of the Service means you accept the updated terms.

## Contact
For questions, contact us through the website.
  `,
  'Privacy Policy': `
**Effective date:** 8 November 2026

## What We Collect
- **URLs and keywords you submit** for analysis. Results may be cached for up to 24 hours to speed up repeat checks.
- **Your IP address** (for IPv6, the network part of it), kept for up to 48 hours to count daily free scans and prevent abuse.
- **Messages you send** through the contact form, including your email address if you give it.

## What We Don't Collect
- No account registration required
- No cookies for tracking or advertising
- API keys you paste in are used only for your request and are never stored

## Services That Process Data for Us
These providers handle data on our behalf and may process it outside New Zealand:
- **Cloudflare**: hosts the website
- **Railway**: runs our analysis server
- **Upstash**: stores temporary usage counters and cached results
- **Google Gemini**: writes AI suggestions and reports; page content you submit is sent to it
- **Google PageSpeed**: checks page speed and, for sites that block us, competitor pages
- **Serper.dev**: fetches Google search results for competitor and position checks
- **Resend / Gmail**: delivers contact-form messages

## Rank Tracker
The rank tracker is paused. Keywords tracked before then are kept until you ask us to remove them.

## Data Retention
Cached results expire within 24 hours. Usage counters expire within 48 hours. Contact messages are kept only as long as needed to reply.

## Your Rights
Under the New Zealand Privacy Act 2020 you can ask to see or correct personal information we hold about you, or ask us to delete it, by contacting us through the website.

## Contact
For privacy questions, contact us through the website.
  `,
  'Cookie Policy': `
**Effective date:** 8 November 2026

## Cookies We Use
RankSpy AI does not set cookies. Daily usage limits are counted on our server, not in your browser.

## Analytics
We may use privacy-respecting analytics tools that do not use cookies or track individuals across sites.

## No Advertising Cookies
We do not use advertising, retargeting, or tracking cookies of any kind.

## Third-Party Cookies
Our third-party services are called from our server, so they do not set cookies in your browser.

## Contact
For cookie-related questions, contact us through the website.
  `,
}

// **bold** anywhere in a line becomes <strong>; nothing else is interpreted
function inline(text) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') && part.length > 4
      ? <strong key={i} style={{ color: '#e6e6e6', fontWeight: 700 }}>{part.slice(2, -2)}</strong>
      : part)
}

function parseMarkdown(text) {
  return text.trim().split('\n').map((line, i) => {
    if (line.startsWith('## ')) return <h3 key={i} style={{ fontSize: '14px', fontWeight: 700, color: '#fff', margin: '20px 0 8px' }}>{line.slice(3)}</h3>
    if (line.startsWith('**Effective date')) return <p key={i} style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>{inline(line)}</p>
    if (line.startsWith('- ')) return <li key={i} style={{ fontSize: '13px', color: 'var(--text-body)', marginLeft: '16px', marginBottom: '4px' }}>{inline(line.slice(2))}</li>
    if (line.trim() === '') return <div key={i} style={{ height: '4px' }} />
    return <p key={i} style={{ fontSize: '13px', color: 'var(--text-body)', lineHeight: 1.6, marginBottom: '4px' }}>{inline(line)}</p>
  })
}

export default function LegalModal({ page, onClose }) {
  return (
    <Modal title={page} onClose={onClose}>
      {parseMarkdown(CONTENT[page] || '')}
    </Modal>
  )
}
