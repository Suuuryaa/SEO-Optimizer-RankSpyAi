import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || (
  import.meta.env.DEV ? 'http://localhost:8000' : (() => { throw new Error('VITE_API_URL is not set') })()
)

const client = axios.create({ baseURL: BASE, timeout: 180000 })

export async function analyzeUrl({ url, keyword, pagespeed = false, geo = false, crawlMode = 'standard' }) {
  const { data } = await client.post('/analyze', { url, keyword, pagespeed, geo, crawl_mode: crawlMode })
  return data
}

export async function findCompetitors({ url, keyword }) {
  const { data } = await client.post('/competitors', { url, keyword })
  return data
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
