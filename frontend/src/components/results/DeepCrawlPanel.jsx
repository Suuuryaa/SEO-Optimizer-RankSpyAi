export default function DeepCrawlPanel({ data }) {
  if (!data) return null
  if (data.error) return (
    <div style={{ background: 'rgba(230,57,70,0.06)', border: '1px solid rgba(230,57,70,0.2)', borderRadius: '10px', padding: '14px 18px', marginTop: '16px', fontSize: '12px', color: '#e63946' }}>
      Deep crawl error: {data.error}
    </div>
  )

  const { pages_crawled, all_h1, all_h2, sub_pages, keyphrases } = data
  const kpList = keyphrases?.keyphrases || []
  const entities = keyphrases?.entities || []

  return (
    <div style={{ background: '#0f0f0f', border: '1px solid #2a2a2a', borderRadius: '12px', padding: '20px', marginTop: '16px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
        <div style={{ fontSize: '11px', color: '#e63946', fontWeight: 700, letterSpacing: '0.08em' }}>
          JS DEEP CRAWL
        </div>
        <div style={{ fontSize: '11px', color: '#555', background: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: '4px', padding: '2px 8px' }}>
          {pages_crawled} pages crawled
        </div>
        {keyphrases?.method && (
          <div style={{ fontSize: '10px', color: '#444', marginLeft: 'auto' }}>
            via {keyphrases.method}
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {/* Keyphrases */}
        {kpList.length > 0 && (
          <div>
            <div style={{ fontSize: '10px', color: '#555', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '8px' }}>
              EXTRACTED KEYPHRASES
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {kpList.map((kp, i) => (
                <span key={i} style={{
                  background: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: '4px',
                  padding: '3px 8px', fontSize: '11px', color: '#ccc',
                }}>
                  {kp}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Named Entities */}
        {entities.length > 0 && (
          <div>
            <div style={{ fontSize: '10px', color: '#555', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '8px' }}>
              NAMED ENTITIES
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {entities.slice(0, 10).map((ent, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{
                    fontSize: '9px', fontWeight: 700, color: '#606060', background: '#1a1a1a',
                    border: '1px solid #2a2a2a', borderRadius: '3px', padding: '1px 5px', minWidth: '30px', textAlign: 'center',
                  }}>
                    {ent.label}
                  </span>
                  <span style={{ fontSize: '12px', color: '#ccc' }}>{ent.word}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Sub-pages discovered */}
      {sub_pages && sub_pages.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <div style={{ fontSize: '10px', color: '#555', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '8px' }}>
            SUB-PAGES DISCOVERED
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {sub_pages.slice(0, 6).map((sp, i) => (
              <div key={i} style={{ background: '#1a1a1a', border: '1px solid #222', borderRadius: '6px', padding: '8px 12px' }}>
                <div style={{ fontSize: '11px', color: '#e63946', marginBottom: '2px', wordBreak: 'break-all' }}>
                  {sp.url}
                </div>
                {sp.title && (
                  <div style={{ fontSize: '12px', color: '#a0a0a0' }}>{sp.title}</div>
                )}
                {sp.h1 && sp.h1.length > 0 && (
                  <div style={{ fontSize: '11px', color: '#606060', marginTop: '2px' }}>
                    H1: {sp.h1[0]}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Headings summary */}
      {all_h2 && all_h2.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <div style={{ fontSize: '10px', color: '#555', fontWeight: 700, letterSpacing: '0.1em', marginBottom: '8px' }}>
            ALL H2 HEADINGS FOUND ({all_h2.length})
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
            {all_h2.slice(0, 20).map((h, i) => (
              <span key={i} style={{
                fontSize: '11px', color: '#777', background: '#151515', border: '1px solid #222',
                borderRadius: '4px', padding: '2px 8px',
              }}>
                {h}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
