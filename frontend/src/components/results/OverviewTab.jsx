import {
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
  RadarChart,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

function scoreColor(score) {
  if (score >= 80) return '#22c55e'
  if (score >= 60) return '#f97316'
  return '#e63946'
}

function scoreLabel(band) {
  const map = {
    excellent: 'EXCELLENT',
    good: 'GOOD',
    needs_improvement: 'NEEDS WORK',
    poor: 'POOR',
  }
  return map[band?.toLowerCase()] || band || 'N/A'
}

function MetricCard({ label, value, unit = '', borderColor = '#e63946', sublabel = '' }) {
  return (
    <div
      className="metric-card"
      style={{
        background: '#161616',
        border: '1px solid #2a2a2a',
        borderLeft: `3px solid ${borderColor}`,
        borderRadius: '8px',
        padding: '16px',
      }}
    >
      <div style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '8px', textTransform: 'uppercase' }}>
        {label}
      </div>
      <div style={{ fontSize: '26px', fontWeight: 800, color: '#fff', lineHeight: 1 }}>
        {value ?? '—'}{unit}
      </div>
      {sublabel && (
        <div style={{ fontSize: '11px', color: '#606060', marginTop: '4px' }}>{sublabel}</div>
      )}
    </div>
  )
}

export default function OverviewTab({ data }) {
  const score = data.seo_score ?? 0
  const color = scoreColor(score)
  const gaugeData = [{ name: 'SEO Score', value: score, fill: color }]

  const radarData = [
    { subject: 'Content', A: Math.min(100, (data.word_count ?? 0) / 10) },
    { subject: 'Keywords', A: Math.min(100, (data.keyword_count ?? 0) * 10) },
    { subject: 'Technical', A: data.technical_seo ? Object.values(data.technical_seo).filter(Boolean).length * 20 : 0 },
    { subject: 'On-Page', A: [data.keyword_in_title, data.keyword_in_meta, data.keyword_in_h1].filter(Boolean).length * 33 },
    { subject: 'Links', A: Math.min(100, ((data.internal_links ?? 0) + (data.external_links ?? 0)) * 5) },
  ]

  return (
    <div className="fade-in">
      {/* Score gauge row */}
      <div style={{ display: 'grid', gridTemplateColumns: '220px 1fr', gap: '20px', marginBottom: '24px', alignItems: 'center' }}>
        {/* Gauge */}
        <div
          style={{
            background: '#161616',
            border: '1px solid #2a2a2a',
            borderRadius: '12px',
            padding: '20px',
            textAlign: 'center',
          }}
        >
          <div style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '12px' }}>
            SEO SCORE
          </div>
          <div style={{ position: 'relative', height: '150px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadialBarChart
                innerRadius="65%"
                outerRadius="90%"
                data={gaugeData}
                startAngle={220}
                endAngle={-40}
                barSize={14}
              >
                <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                <RadialBar
                  background={{ fill: '#222' }}
                  dataKey="value"
                  angleAxisId={0}
                  cornerRadius={8}
                />
              </RadialBarChart>
            </ResponsiveContainer>
            <div
              style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                textAlign: 'center',
                marginTop: '8px',
              }}
            >
              <div style={{ fontSize: '32px', fontWeight: 900, color, lineHeight: 1 }}>{score}</div>
              <div style={{ fontSize: '10px', fontWeight: 700, color: color, letterSpacing: '0.06em', marginTop: '2px' }}>
                {scoreLabel(data.score_band)}
              </div>
            </div>
          </div>
        </div>

        {/* Radar */}
        <div
          style={{
            background: '#161616',
            border: '1px solid #2a2a2a',
            borderRadius: '12px',
            padding: '20px',
          }}
        >
          <div style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '8px' }}>
            SEO RADAR
          </div>
          <ResponsiveContainer width="100%" height={150}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#2a2a2a" />
              <PolarAngleAxis dataKey="subject" tick={{ fill: '#606060', fontSize: 11 }} />
              <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
              <Radar dataKey="A" stroke="#e63946" fill="#e63946" fillOpacity={0.15} strokeWidth={2} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Metric cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '24px' }}>
        <MetricCard label="Word Count" value={data.word_count?.toLocaleString()} borderColor="#3b82f6" />
        <MetricCard label="Keyword Hits" value={data.keyword_count} borderColor="#e63946" />
        <MetricCard label="Keyword Density" value={data.keyword_density != null ? `${data.keyword_density}` : '—'} unit="%" borderColor="#22c55e" />
        <MetricCard label="Internal Links" value={data.internal_links} borderColor="#a855f7" />
        <MetricCard label="External Links" value={data.external_links} borderColor="#f97316" />
        <MetricCard label="Missing ALTs" value={data.missing_alt} borderColor="#eab308" sublabel="images without alt text" />
      </div>

      {/* Keyword placement */}
      <div
        style={{
          background: '#161616',
          border: '1px solid #2a2a2a',
          borderRadius: '12px',
          padding: '20px',
        }}
      >
        <div style={{ fontSize: '11px', color: '#606060', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '16px' }}>
          KEYWORD PLACEMENT
        </div>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          {[
            { label: 'In Title', val: data.keyword_in_title },
            { label: 'In Meta', val: data.keyword_in_meta },
            { label: 'In H1', val: data.keyword_in_h1 },
          ].map(({ label, val }) => (
            <div
              key={label}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                background: val ? 'rgba(34,197,94,0.08)' : 'rgba(230,57,70,0.08)',
                border: `1px solid ${val ? 'rgba(34,197,94,0.25)' : 'rgba(230,57,70,0.25)'}`,
                borderRadius: '8px',
                padding: '10px 16px',
                flex: 1,
                minWidth: '120px',
              }}
            >
              <span style={{ fontSize: '16px' }}>{val ? '✅' : '❌'}</span>
              <span style={{ fontSize: '13px', fontWeight: 600, color: val ? '#22c55e' : '#e63946' }}>{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
