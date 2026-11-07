const BASE = import.meta.env.VITE_API_URL || (
  import.meta.env.DEV ? 'http://localhost:8000' : (() => { throw new Error('VITE_API_URL is not set') })()
)

const REQUEST_TIMEOUT = 180000

const sleep = ms => new Promise(r => setTimeout(r, ms))

const MESSAGES = {
  not_found: "That page returned 'not found'. Check the URL.",
  server_error: 'That site returned a server error. Try again later.',
  blocked: 'This site blocked our scanner.',
  timeout: 'That site is slow to respond. Try again in a minute.',
  unreachable: "We couldn't find that domain.",
  not_html: "That URL isn't a web page.",
  rate_limited: "Today's free scans are used up.",
  daily_limit: () => `You've used today's free scans. More at ${resetTimeLocal()} (your time). Rescanning a page you already scanned is still free.`,
  compare_limit: () => `You've used today's free competitor comparison. More at ${resetTimeLocal()} (your time).`,
  too_many_running: 'You already have 2 scans running. Wait for one to finish, then try again.',
  busy: 'Our server is busy. Try again in a minute.',
  network: "Can't reach our server. Check your connection.",
  invalid_input: "We couldn't read that page. Check the URL and try again.",
  expired: 'This scan is no longer available. Please run it again.',
  cancelled: 'Scan cancelled.',
}

export function messageFor(kind) {
  const m = MESSAGES[kind]
  if (typeof m === 'function') return m()
  return m || 'Something went wrong. Please try again.'
}

// Free allowances reset at 00:00 UTC; show that moment in the visitor's own time.
export function resetTimeLocal(iso) {
  const d = iso ? new Date(iso) : (() => {
    const n = new Date()
    return new Date(Date.UTC(n.getUTCFullYear(), n.getUTCMonth(), n.getUTCDate() + 1))
  })()
  return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

export const AI_REPORT_UNAVAILABLE =
  "AI strategy report isn't available right now. Your scores and to-do list are unaffected."

// Every failure becomes ApiError { status, kind, message }.
// `message` is always our own product copy (messageFor); raw backend text
// is kept on `detail` for debugging only and must never be rendered.
export class ApiError extends Error {
  constructor({ status = 0, kind = 'internal', detail = '' } = {}) {
    super(messageFor(kind))
    this.name = 'ApiError'
    this.status = status
    this.kind = kind
    this.detail = detail
  }
}

function kindFromStatus(status, detail) {
  if (status === 429) {
    return /already have \d+ scans? running/i.test(String(detail || '')) ? 'too_many_running' : 'rate_limited'
  }
  if (status === 503) return 'busy'
  if (status === 504) return 'timeout'
  if (status === 422 || status === 400) return 'invalid_input'
  return 'internal'
}

async function request(method, path, body, { signal } = {}) {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT)
  const onAbort = () => ctrl.abort()
  signal?.addEventListener('abort', onAbort)
  let res
  try {
    res = await fetch(BASE + path, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    })
  } catch {
    if (signal?.aborted) throw new ApiError({ kind: 'cancelled' })
    if (ctrl.signal.aborted) throw new ApiError({ kind: 'timeout' })
    throw new ApiError({ kind: 'network' })
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', onAbort)
  }
  let data = null
  try { data = await res.json() } catch { data = null }
  if (!res.ok) {
    const detail = data?.detail
    throw new ApiError({ status: res.status, kind: kindFromStatus(res.status, detail), detail })
  }
  return data
}

// Scans run as background jobs: start one, then poll until it finishes.
// Each request is short, so Railway's 60 s request limit no longer applies.
async function runJob(path, body, onProgress, signal) {
  const data = await request('POST', path, body, { signal })
  const started = Date.now()
  let failures = 0
  for (;;) {
    await sleep(1500)
    if (signal?.aborted) throw new ApiError({ kind: 'cancelled' })
    let job
    try {
      job = await request('GET', `/jobs/${data.job_id}`, undefined, { signal })
      failures = 0
    } catch (err) {
      if (err?.kind === 'cancelled') throw err
      if (err?.status === 404) throw new ApiError({ status: 404, kind: 'expired' })
      if (++failures >= 4) throw err
      continue
    }
    onProgress?.({ step: job.step, steps: job.steps || [], elapsed: job.elapsed })
    if (job.status === 'done') return job.result
    if (job.status === 'error') {
      const status = job.status_code || 0
      throw new ApiError({ status, kind: job.error_kind || kindFromStatus(status, job.error), detail: job.error })
    }
    if (Date.now() - started > 240000) throw new ApiError({ status: 504, kind: 'timeout' })
  }
}

export function analyzeUrl({ url, keyword, pagespeed = false, geo = false, crawlMode = 'standard', fresh = false, userApiKeys, onProgress, signal }) {
  const body = { url, keyword, pagespeed, geo, crawl_mode: crawlMode, user_api_keys: userApiKeys }
  if (fresh) body.fresh = true
  return runJob('/jobs/analyze', body, onProgress, signal)
}

export function findCompetitors({ url, keyword, userApiKeys, onProgress, signal }) {
  return runJob('/jobs/competitors', { url, keyword, user_api_keys: userApiKeys }, onProgress, signal)
}

export function suggestMeta({ url, keyword }) {
  return request('POST', '/suggest-meta', { url, keyword })
}

export function generateSchema({ url, keyword }) {
  return request('POST', '/schema', { url, keyword })
}

export function healthCheck() {
  return request('GET', '/health')
}

export function getRateStatus() {
  return request('GET', '/rate-status')
}

export function analyzeLocalSeo({ url, keyword }) {
  return request('POST', '/local-seo', { url, keyword })
}

export function trackKeyword({ url, keyword }) {
  return request('POST', '/track', { url, keyword })
}

export function getRankings(url) {
  return request('GET', `/rankings?url=${encodeURIComponent(url)}`)
}
