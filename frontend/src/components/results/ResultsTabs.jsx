import { useState } from 'react'
import OverviewTab from './OverviewTab'
import TechnicalTab from './TechnicalTab'
import ContentTab from './ContentTab'
import RecommendationsTab from './RecommendationsTab'

const TABS = [
  { id: 'overview', label: '📊 Overview' },
  { id: 'technical', label: '⚙️ Technical' },
  { id: 'content', label: '📝 Content' },
  { id: 'recommendations', label: '💡 Recommendations' },
]

export default function ResultsTabs({ data }) {
  const [active, setActive] = useState('overview')

  const recCount = data.recommendations?.length ?? 0

  return (
    <div
      style={{
        background: '#161616',
        border: '1px solid #2a2a2a',
        borderRadius: '12px',
        overflow: 'hidden',
        marginTop: '24px',
      }}
    >
      {/* Tab header */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid #2a2a2a',
          background: '#111',
          overflowX: 'auto',
        }}
      >
        {TABS.map((tab) => {
          const isActive = active === tab.id
          return (
            <button
              key={tab.id}
              className="tab-btn"
              onClick={() => setActive(tab.id)}
              style={{
                background: 'none',
                border: 'none',
                borderBottom: isActive ? '2px solid #e63946' : '2px solid transparent',
                color: isActive ? '#fff' : '#606060',
                padding: '14px 20px',
                fontSize: '13px',
                fontWeight: isActive ? 700 : 500,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                position: 'relative',
              }}
            >
              {tab.label}
              {tab.id === 'recommendations' && recCount > 0 && (
                <span
                  style={{
                    background: '#e63946',
                    color: '#fff',
                    fontSize: '10px',
                    fontWeight: 800,
                    borderRadius: '100px',
                    padding: '1px 6px',
                    marginLeft: '6px',
                  }}
                >
                  {recCount}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      <div style={{ padding: '24px' }}>
        {active === 'overview' && <OverviewTab data={data} />}
        {active === 'technical' && <TechnicalTab data={data} />}
        {active === 'content' && <ContentTab data={data} />}
        {active === 'recommendations' && <RecommendationsTab data={data} />}
      </div>
    </div>
  )
}
