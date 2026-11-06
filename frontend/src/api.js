import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || (
  import.meta.env.DEV ? 'http://localhost:8000' : (() => { throw new Error('VITE_API_URL is not set') })()
)

const client = axios.create({ baseURL: BASE, timeout: 180000 })

const sleep = ms => new Promise(r => setTimeout(r, ms))

// Errors are shaped like axios errors so callers keep reading err.response.data.detail
function jobError(detail, status) {
  const e = new Error(detail)
  e.response = { status, data: { detail } }
  return e
}

// Scans run as background jobs: start one, then poll until it finishes.
// Each request is short, so Railway's 60 s request limit no longer applies.
async function runJob(path, body, onProgress) {
  const { data } = await client.post(path, body)
  const started = Date.now()
  let failures = 0
  for (;;) {
    await sleep(1500)
    let job
    try {
      ({ data: job } = await client.get(`/jobs/${data.job_id}`))
      failures = 0
    } catch (err) {
      if (err?.response?.status === 404) throw jobError('The server restarted during your scan. Please run it again.', 404)
      if (++failures >= 4) throw err
      continue
    }
    onProgress?.({ step: job.step, steps: job.steps || [], elapsed: job.elapsed })
    if (job.status === 'done') return job.result
    if (job.status === 'error') throw jobError(job.error || 'Scan failed. Please try again.', job.status_code)
    if (Date.now() - started > 240000) throw jobError('The scan is taking too long. Please try again.', 504)
  }
}

export async function analyzeUrl({ url, keyword, pagespeed = false, geo = false, crawlMode = 'standard', userApiKeys, onProgress }) {
  return runJob('/jobs/analyze', { url, keyword, pagespeed, geo, crawl_mode: crawlMode, user_api_keys: userApiKeys }, onProgress)
}

export async function findCompetitors({ url, keyword, userApiKeys, onProgress }) {
  return runJob('/jobs/competitors', { url, keyword, user_api_keys: userApiKeys }, onProgress)
}

export async function suggestMeta({ url, keyword }) {
  const { data } = await client.post('/suggest-meta', { url, keyword })
  return data
}

export async function generateSchema({ url, keyword }) {
  const { data } = await client.post('/schema', { url, keyword })
  return data
}

export async function healthCheck() {
  const { data } = await client.get('/health')
  return data
}

export async function getRateStatus() {
  const { data } = await client.get('/rate-status')
  return data
}

export async function analyzeLocalSeo({ url, keyword }) {
  const { data } = await client.post('/local-seo', { url, keyword })
  return data
}

export async function trackKeyword({ url, keyword }) {
  const { data } = await client.post('/track', { url, keyword })
  return data
}

export async function getRankings(url) {
  const { data } = await client.get(`/rankings?url=${encodeURIComponent(url)}`)
  return data
}
