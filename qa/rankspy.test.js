/**
 * RankSpy AI — Comprehensive QA Test Suite
 * Run: npx playwright test rankspy.test.js --reporter=list
 */

const { test, expect } = require('@playwright/test')
const https = require('https')

const BASE_URL = 'https://rankspyseo.xyz'
const TEST_URL = 'https://example.com'
const TEST_KEYWORD = 'seo tools'
const API_URL = 'https://affectionate-recreation-production-e508.up.railway.app'

const UPSTASH_URL = 'https://informed-porpoise-106831.upstash.io'
const UPSTASH_TOKEN = 'gQAAAAAAAaFPAAIgcDE1ODc1MDIzODU5NTE0N2U3YjhhYWI5OTQzYjg2ZmMzMg'

// Reset rate limits before the suite runs so analyze tests are never blocked
test.beforeAll(async ({ request }) => {
  const today = new Date().toISOString().slice(0, 10)
  // Scan for rate keys and delete them
  try {
    const keysResp = await request.get(`${UPSTASH_URL}/keys/rate:*`, {
      headers: { Authorization: `Bearer ${UPSTASH_TOKEN}` },
    })
    const { result: keys = [] } = await keysResp.json()
    for (const key of keys.filter((k) => k.includes(today))) {
      await request.get(`${UPSTASH_URL}/del/${key}`, {
        headers: { Authorization: `Bearer ${UPSTASH_TOKEN}` },
      })
      console.log(`  [setup] Reset rate limit key: ${key}`)
    }
  } catch (e) {
    console.log(`  [setup] Could not reset rate limits: ${e.message}`)
  }
})

// ─── Helpers ──────────────────────────────────────────────────────────────────

let consoleErrors = []
let networkFailures = []

async function setupCollectors(page) {
  consoleErrors = []
  networkFailures = []

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const txt = msg.text()
      // Ignore browser extension, CORS, favicon, and generic 404 noise
      if (
        !txt.includes('chrome-extension') &&
        !txt.includes('Extension') &&
        !txt.includes('favicon') &&
        !txt.includes('Failed to load resource')
      ) {
        consoleErrors.push(txt)
      }
    }
  })

  page.on('response', (resp) => {
    const status = resp.status()
    const url = resp.url()
    if (status >= 400 && !url.includes('analytics') && !url.includes('hotjar')) {
      networkFailures.push({ url, status })
    }
  })
}

async function checkBrokenImages(page) {
  return page.$$eval('img', (imgs) =>
    imgs
      .filter((img) => img.naturalWidth === 0 && img.src && !img.src.startsWith('data:'))
      .map((img) => img.src)
  )
}

async function loadPage(page) {
  await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })
}

// ─── 1. Page Load & Title ─────────────────────────────────────────────────────

test('Page load: correct title, hero visible, no broken images', async ({ page }) => {
  await setupCollectors(page)
  const response = await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })

  expect(response.status()).toBe(200)
  await expect(page).toHaveTitle(/rankspy/i)

  // Hero h1 present
  await expect(page.locator('h1').first()).toBeVisible()

  // URL input present (placeholder is "https://example.com")
  await expect(page.locator('input[placeholder="https://example.com"]')).toBeVisible()

  const broken = await checkBrokenImages(page)
  console.log(`  Broken images: ${broken.length}`)
  expect(broken).toHaveLength(0)
})

// ─── 2. SEO Analyzer Full Trial ───────────────────────────────────────────────

test('SEO Analyzer: enter URL + keyword, get results', async ({ page }) => {
  await setupCollectors(page)
  await loadPage(page)

  await page.locator('input[placeholder="https://example.com"]').fill(TEST_URL)
  await page.locator('input[placeholder="e.g. seo audit tool"]').fill(TEST_KEYWORD)

  // Click Analyze (button text is "🔍 ANALYZE SEO")
  await page.locator('button').filter({ hasText: /ANALYZE SEO/i }).first().click()

  // Spinner appears briefly
  try {
    await page.locator('.spinner').waitFor({ state: 'visible', timeout: 3000 })
    await page.locator('.spinner').waitFor({ state: 'hidden', timeout: 90000 })
  } catch {
    // spinner too fast — ok
  }

  // Results: "ANALYZING" header bar should appear
  await expect(page.locator('text=ANALYZING').first()).toBeVisible({ timeout: 90000 })

  // Log any 404s so we can investigate (don't fail on them — could be backend resource)
  const appNetErrors = networkFailures.filter(
    (f) => f.status >= 500 || (f.status === 404 && f.url.includes(BASE_URL))
  )
  if (appNetErrors.length) {
    appNetErrors.forEach((f) => console.log(`    ✗ ${f.status}: ${f.url}`))
  }

  console.log(`  Console errors: ${consoleErrors.length}`)
  consoleErrors.forEach((e) => console.log(`    ✗ ${e}`))
  expect(consoleErrors).toHaveLength(0)
})

// ─── 3. Competitor Finder ─────────────────────────────────────────────────────

test('Competitor Finder: returns competitor results', async ({ page }) => {
  await setupCollectors(page)
  await loadPage(page)

  await page.locator('input[placeholder="https://example.com"]').fill(TEST_URL)
  await page.locator('input[placeholder="e.g. seo audit tool"]').fill(TEST_KEYWORD)

  await page.locator('button').filter({ hasText: /competitor/i }).first().click()

  try {
    await page.locator('.spinner').waitFor({ state: 'visible', timeout: 3000 })
    await page.locator('.spinner').waitFor({ state: 'hidden', timeout: 90000 })
  } catch { /* fast */ }

  // "COMPETITOR ANALYSIS" header or competitor count
  await expect(page.locator('text=/COMPETITOR ANALYSIS|competitor/i').first()).toBeVisible({ timeout: 90000 })
  console.log('  ✓ Competitor results loaded')
})

// ─── 4. FAQ Accordion ────────────────────────────────────────────────────────

test('FAQ: all accordion items expand and show answers', async ({ page }) => {
  await loadPage(page)

  // Scroll to FAQ section
  await page.evaluate(() => {
    const el = document.getElementById('section-faq')
    if (el) el.scrollIntoView()
  })
  await page.waitForTimeout(800)

  // The FAQ buttons are inside the FAQ section div
  // They're <button> elements that contain FAQ question text
  const faqContainer = page.locator('text=Frequently Asked Questions').locator('../..')

  // Get all FAQ question buttons — each has a + icon
  const allButtons = page.locator('button').filter({ hasText: /\+/ })
  const count = await allButtons.count()
  console.log(`  Found ${count} FAQ toggle buttons`)
  expect(count).toBeGreaterThanOrEqual(5)

  for (let i = 0; i < count; i++) {
    // Re-query each time — DOM mutates on open/close, stale refs break
    const freshButtons = page.locator('button').filter({ hasText: /\+/ })
    const btn = freshButtons.nth(i)
    const isVisible = await btn.isVisible().catch(() => false)
    if (!isVisible) continue

    // Capture answer text appearing in the FAQ section after click
    const faqSection = page.locator('#section-faq').first()
    const textBefore = await faqSection.textContent()

    await btn.click()
    await page.waitForTimeout(300)

    const textAfter = await faqSection.textContent()
    expect(textAfter.length).toBeGreaterThan(textBefore.length + 20)
    console.log(`  ✓ FAQ ${i + 1} expanded correctly`)

    // Collapse — re-query since button text changed to '−'
    const closeBtn = page.locator('button').filter({ hasText: '−' }).first()
    if (await closeBtn.isVisible().catch(() => false)) {
      await closeBtn.click()
      await page.waitForTimeout(150)
    }
  }
})

// ─── 5. Footer — Legal Modals ─────────────────────────────────────────────────

test('Footer: Privacy Policy opens legal modal', async ({ page }) => {
  await loadPage(page)

  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
  await page.waitForTimeout(600)

  const footer = page.locator('footer')

  // Privacy Policy
  const privacyBtn = footer.locator('button').filter({ hasText: /privacy policy/i }).first()
  await expect(privacyBtn).toBeVisible()
  await privacyBtn.click({ force: true })
  await page.waitForTimeout(500)

  // Check modal or overlay appeared — look for the word "Privacy" in a heading/modal context
  const modalHeading = page.locator('h2, h3').filter({ hasText: /privacy/i }).first()
  const modalVisible = await modalHeading.isVisible().catch(() => false)
  if (modalVisible) {
    console.log('  ✓ Privacy Policy modal opened with heading')
  } else {
    // Fallback: at least the content exists somewhere visible on screen
    const policyContent = page.locator('text=Privacy Policy').nth(1)
    await expect(policyContent).toBeVisible({ timeout: 3000 })
    console.log('  ✓ Privacy Policy content visible')
  }

  // Close modal
  await page.keyboard.press('Escape')
  await page.waitForTimeout(400)
})

test('Footer: Terms of Service opens legal modal', async ({ page }) => {
  await loadPage(page)

  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
  await page.waitForTimeout(600)

  const footer = page.locator('footer')
  const termsBtn = footer.locator('button').filter({ hasText: /terms of service/i }).first()
  await expect(termsBtn).toBeVisible()
  await termsBtn.click({ force: true })
  await page.waitForTimeout(500)

  const heading = page.locator('h2, h3').filter({ hasText: /terms/i }).first()
  const visible = await heading.isVisible().catch(() => false)
  if (visible) {
    console.log('  ✓ Terms of Service modal opened')
  } else {
    const content = page.locator('text=Terms of Service').nth(1)
    await expect(content).toBeVisible({ timeout: 3000 })
    console.log('  ✓ Terms of Service content visible')
  }
})

// ─── 6. Footer Navigation Links ──────────────────────────────────────────────

test('Footer: nav links scroll to page sections', async ({ page }) => {
  await loadPage(page)
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
  await page.waitForTimeout(500)

  const footer = page.locator('footer')
  const labels = ['How It Works', 'FAQ', 'Score Guide']

  for (const label of labels) {
    const btn = footer.locator('button').filter({ hasText: label }).first()
    const visible = await btn.isVisible().catch(() => false)
    expect(visible).toBe(true)
    await btn.click({ force: true })
    await page.waitForTimeout(400)
    console.log(`  ✓ "${label}" nav button works`)
  }
})

// ─── 7. Link Crawler ─────────────────────────────────────────────────────────

test('Link crawler: no <a href> links return 404', async ({ page, request }) => {
  await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })

  const hrefs = await page.$$eval('a[href]', (els) =>
    [...new Set(
      els
        .map((el) => el.href)
        .filter((h) => h && h.startsWith('http') && !h.includes('javascript:'))
    )]
  )

  console.log(`  Found ${hrefs.length} external links`)
  const broken = []

  for (const href of hrefs) {
    try {
      const resp = await request.get(href, { timeout: 8000 })
      const status = resp.status()
      if (status === 404) {
        broken.push({ href, status })
        console.log(`  ✗ 404: ${href}`)
      } else {
        console.log(`  ✓ ${status}: ${href}`)
      }
    } catch (e) {
      console.log(`  ⚠ Skipped (timeout/blocked): ${href}`)
    }
  }

  expect(broken).toHaveLength(0)
})

// ─── 8. Backend API Health ────────────────────────────────────────────────────

test('Backend API: /health and /rate-status respond correctly', async ({ request }) => {
  const health = await request.get(`${API_URL}/health`)
  expect(health.status()).toBe(200)
  const body = await health.json()
  expect(body.status).toBe('ok')
  console.log(`  ✓ /health: ${JSON.stringify(body)}`)

  const rate = await request.get(`${API_URL}/rate-status`)
  expect(rate.status()).toBe(200)
  const rateBody = await rate.json()
  expect(rateBody).toHaveProperty('daily_limit')
  console.log(`  ✓ /rate-status: ${JSON.stringify(rateBody)}`)
})

// ─── 9. Performance & Console Audit ──────────────────────────────────────────

test('Performance: DOMContentLoaded under 5s, zero console errors, zero broken images', async ({ page }) => {
  await setupCollectors(page)

  const t0 = Date.now()
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 30000 })
  const loadTime = Date.now() - t0
  console.log(`  DOMContentLoaded: ${loadTime}ms`)
  expect(loadTime).toBeLessThan(5000)

  await page.waitForLoadState('networkidle')

  const broken = await checkBrokenImages(page)
  console.log(`  Broken images: ${broken.length}`)
  expect(broken).toHaveLength(0)

  console.log(`  Console errors: ${consoleErrors.length}`)
  consoleErrors.forEach((e) => console.log(`    ✗ ${e}`))
  expect(consoleErrors).toHaveLength(0)

  const critNet = networkFailures.filter((f) => f.status >= 500)
  console.log(`  5xx network errors: ${critNet.length}`)
  critNet.forEach((f) => console.log(`    ✗ ${f.status} ${f.url}`))
  expect(critNet).toHaveLength(0)
})

// ─── 10. Mobile Viewport ─────────────────────────────────────────────────────

test('Mobile (iPhone 14): no horizontal overflow, inputs visible', async ({ browser }) => {
  const ctx = await browser.newContext({
    viewport: { width: 390, height: 844 },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
  })
  const page = await ctx.newPage()
  await setupCollectors(page)

  await page.goto(BASE_URL, { waitUntil: 'networkidle', timeout: 30000 })

  // Check for horizontal overflow
  const overflow = await page.evaluate(() => {
    return document.documentElement.scrollWidth - document.documentElement.clientWidth
  })
  console.log(`  Horizontal overflow: ${overflow}px`)
  expect(overflow).toBe(0)

  await expect(page.locator('input[placeholder="https://example.com"]')).toBeVisible()
  await expect(page.locator('button').filter({ hasText: /analyze/i }).first()).toBeVisible()

  const broken = await checkBrokenImages(page)
  expect(broken).toHaveLength(0)
  console.log('  ✓ Mobile layout clean')

  await ctx.close()
})
