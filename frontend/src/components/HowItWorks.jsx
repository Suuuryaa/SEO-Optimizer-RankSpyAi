import { useReveal } from '../lib/useReveal'

const STEPS = [
  {
    number: '01',
    title: 'Enter Your URL',
    desc: 'Paste any webpage URL and your target keyword into the analyzer.',
  },
  {
    number: '02',
    title: 'We Crawl & Analyze',
    desc: 'RankSpy AI fetches your page like a search engine bot and runs 30+ on-page checks, usually in about a minute.',
  },
  {
    number: '03',
    title: 'Get Actionable Insights',
    desc: 'Receive a scored report with prioritized fixes, competitor data, and AI recommendations.',
  },
]

export default function HowItWorks() {
  const sectionRef = useReveal()

  return (
    <div ref={sectionRef} style={{ padding: '48px 0' }}>
      <div style={{ maxWidth: '1088px', margin: '0 auto' }}>
        <div className="reveal" style={{ textAlign: 'center', marginBottom: '56px' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, color: '#e63946', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: '16px' }}>
            The process
          </div>
          <h2 style={{ fontSize: 'clamp(28px, 5vw, 44px)', fontWeight: 800, color: '#fff', letterSpacing: '-1.5px' }}>
            How It Works
          </h2>
        </div>

        <div style={{ position: 'relative' }}>
          {/* Animated connector line */}
          <div className="how-line" style={{ position: 'absolute', top: '28px', left: '16.6%', right: '16.6%', height: '1px', overflow: 'hidden' }}>
            <div style={{ height: '100%', background: 'linear-gradient(90deg, #e63946, rgba(230,57,70,0.3))' }} />
          </div>

          <div className="how-steps" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'center' }}>
            {STEPS.map((step, i) => (
              <div
                key={step.number}
                className="reveal"
                style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '0 16px', transitionDelay: `${0.1 + i * 0.15}s` }}
              >
                <div
                  style={{
                    width: '56px',
                    height: '56px',
                    borderRadius: '50%',
                    background: '#0d0d0d',
                    border: '1px solid #2a2a2a',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '28px',
                    position: 'relative',
                    zIndex: 1,
                    flexShrink: 0,
                  }}
                >
                  <span style={{ fontSize: '13px', fontWeight: 800, color: '#e63946', letterSpacing: '0.05em' }}>
                    {step.number}
                  </span>
                </div>
                <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#fff', margin: '0 0 12px', letterSpacing: '-0.3px' }}>
                  {step.title}
                </h3>
                <div style={{ fontSize: '13px', color: '#a0a0a0', lineHeight: '1.65', maxWidth: '220px' }}>
                  {step.desc}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
