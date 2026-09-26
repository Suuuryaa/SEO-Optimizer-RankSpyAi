/**
 * RankSpy AI — Frontend Security & E2E Audit
 * Lead AppSec Reviewer + QA Automation Engineer
 *
 * Run: node security/frontend_e2e_audit.js
 * Run against staging: TARGET_URL=https://rankspyseo.xyz node security/frontend_e2e_audit.js
 */

const { chromium } = require('playwright');

const TARGET = process.env.TARGET_URL || 'https://rankspyseo.xyz';
const PASS = '\x1b[32m✔\x1b[0m';
const FAIL = '\x1b[31m✘\x1b[0m';
const WARN = '\x1b[33m⚠\x1b[0m';
const HEAD = '\x1b[36m';
const RESET = '\x1b[0m';

let passed = 0, failed = 0, warned = 0;

function log(icon, label, detail = '') {
  const line = `  ${icon} ${label}${detail ? ' — ' + detail : ''}`;
  console.log(line);
  if (icon === PASS) passed++;
  else if (icon === FAIL) failed++;
  else if (icon === WARN) warned++;
}

function section(title) {
  console.log(`\n${HEAD}━━━ ${title} ━━━${RESET}`);
}

// ─────────────────────────────────────────────
// SECRETS TO NEVER APPEAR IN CLIENT-SIDE CODE
// ─────────────────────────────────────────────
const FORBIDDEN_PATTERNS = [
  { label: 'Serper API key',      re: /caa47a6a54fe4d24/ },
  { label: 'PageSpeed API key',   re: /AIzaSy[A-Za-z0-9_-]{33}/ },
  { label: 'Gemini API key',      re: /AIzaSy[A-Za-z0-9_-]{33}/ },
  { label: 'Upstash token',       re: /gQAAAAAAAa/ },
  { label: 'HuggingFace token',   re: /hf_[A-Za-z0-9]{20,}/ },
  { label: 'Resend API key',      re: /re_[A-Za-z0-9_]{20,}/ },
  { label: 'Admin password',      re: /suryaisthegoat/ },
  { label: 'Gmail app password',  re: /ypca peiq|ypca_peiq/ },
  { label: 'ZenRows key',         re: /1220827d/ },
  { label: 'ScraperAPI key',      re: /2f9d0213/ },
  { label: 'Upstash URL',         re: /informed-porpoise/ },
  { label: 'Private IP',          re: /192\.168\.|10\.0\.|172\.16\./ },
];

(async () => {
  console.log(`\n${'═'.repeat(60)}`);
  console.log(` RankSpy AI — Frontend Security & E2E Audit`);
  console.log(` Target: ${TARGET}`);
  console.log(`${'═'.repeat(60)}`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36'
  });
  const page = await context.newPage();

  const consoleLogs = [];
  const networkRequests = [];
  const networkResponses = [];
  const jsErrors = [];

  page.on('console', m => consoleLogs.push({ type: m.type(), text: m.text() }));
  page.on('pageerror', e => jsErrors.push(e.message));
  page.on('request', r => networkRequests.push({ url: r.url(), method: r.method() }));
  page.on('response', async r => {
    const ct = r.headers()['content-type'] || '';
    if (ct.includes('application/json')) {
      const body = await r.text().catch(() => '');
      networkResponses.push({ url: r.url(), status: r.status(), body });
    }
  });

  // ─── 1. PAGE LOAD ───────────────────────────────────────
  section('1 · Page Load & Initial Render');
  await page.goto(TARGET, { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(2000);

  const title = await page.title();
  log(title ? PASS : FAIL, 'Page has a title', title);

  const h1 = await page.$('h1, [class*="hero"] h2, [class*="headline"]');
  log(h1 ? PASS : WARN, 'Hero heading present');

  // ─── 2. CLIENT-SIDE SECRET SCAN (HTML source) ───────────
  section('2 · HTML Source Secret Scan');
  const htmlSource = await page.content();
  for (const { label, re } of FORBIDDEN_PATTERNS) {
    if (re.test(htmlSource)) {
      log(FAIL, `Secret found in HTML DOM`, label);
    } else {
      log(PASS, `Not in HTML`, label);
    }
  }

  // ─── 3. JS BUNDLE SECRET SCAN ───────────────────────────
  section('3 · Production JS Bundle Secret Scan');
  const bundleUrl = await page.evaluate(() => {
    const scripts = Array.from(document.querySelectorAll('script[src]'));
    return scripts.map(s => s.src).find(s => s.includes('/assets/index'));
  });

  if (bundleUrl) {
    const bundleResp = await page.request.get(bundleUrl);
    const bundleText = await bundleResp.text();
    log(PASS, 'JS bundle fetched', bundleUrl.split('/').pop());

    for (const { label, re } of FORBIDDEN_PATTERNS) {
      if (re.test(bundleText)) {
        log(FAIL, `Secret in JS bundle`, label);
      } else {
        log(PASS, `Not in bundle`, label);
      }
    }

    // Check Railway URL is exposed (expected, low-risk — just document it)
    const hasRailwayUrl = /affectionate-recreation/.test(bundleText);
    log(hasRailwayUrl ? WARN : PASS,
      hasRailwayUrl ? 'Railway URL visible in bundle (expected, low-risk)' : 'No Railway URL in bundle');

    // Localhost leaking into production?
    const hasLocalhost = /localhost:8000/.test(bundleText);
    log(hasLocalhost ? WARN : PASS,
      hasLocalhost ? 'localhost:8000 in bundle (dev fallback — benign)' : 'No raw localhost in bundle');

  } else {
    log(WARN, 'No index JS bundle found via script[src]');
  }

  // ─── 4. CONSOLE LOG LEAK CHECK ──────────────────────────
  section('4 · Browser Console Leak Check');
  // Interact to trigger potential debug logs
  const inputs = await page.$$('input[type="text"], input[type="url"]');
  if (inputs[0]) await inputs[0].fill('https://example.com').catch(() => {});
  await page.waitForTimeout(500);

  const debugLogs = consoleLogs.filter(l => ['log', 'debug', 'info'].includes(l.type));
  const errorLogs = consoleLogs.filter(l => l.type === 'error');

  if (debugLogs.length === 0) {
    log(PASS, 'No console.log/debug/info output detected');
  } else {
    for (const l of debugLogs) log(WARN, `console.${l.type}`, l.text.substring(0, 100));
  }

  if (errorLogs.length === 0) {
    log(PASS, 'No console.error output');
  } else {
    for (const l of errorLogs) log(WARN, `console.error`, l.text.substring(0, 120));
  }

  if (jsErrors.length === 0) {
    log(PASS, 'No uncaught JS errors');
  } else {
    for (const e of jsErrors) log(FAIL, 'JS error', e.substring(0, 120));
  }

  // ─── 5. NAVBAR NAVIGATION ───────────────────────────────
  section('5 · Navbar Links & Scroll Navigation');
  const navButtons = await page.$$('nav button');
  let navClicked = 0;
  for (const btn of navButtons) {
    const text = await btn.innerText().catch(() => '');
    if (text && !text.toLowerCase().includes('analyze')) {
      await btn.click().catch(() => {});
      await page.waitForTimeout(300);
      navClicked++;
    }
  }
  log(navClicked > 0 ? PASS : WARN, `Navbar links clicked`, `${navClicked} items`);

  // ─── 6. FAQ ACCORDIONS ──────────────────────────────────
  section('6 · FAQ Accordion Interaction');
  await page.evaluate(() => {
    const el = document.getElementById('section-faq');
    if (el) el.scrollIntoView();
  });
  await page.waitForTimeout(500);

  const faqItems = await page.$$('#section-faq button, [id*="faq"] button, [class*="faq"] button');
  let faqOpened = 0;
  for (const item of faqItems.slice(0, 5)) {
    await item.click().catch(() => {});
    await page.waitForTimeout(200);
    faqOpened++;
  }
  log(faqOpened > 0 ? PASS : WARN, `FAQ items toggled`, `${faqOpened} opened`);

  // ─── 7. SEO TOOL SUBMISSION ─────────────────────────────
  section('7 · SEO Tool Submission (Full Flow)');
  // Scroll to top / input
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);

  const urlInput = await page.$('input[type="url"], input[placeholder*="url" i], input[placeholder*="website" i], input[placeholder*="http" i]');
  if (urlInput) {
    await urlInput.fill('https://example.com');
    log(PASS, 'URL input found and filled');

    const submitBtn = await page.$('button[type="submit"]:not([disabled]), button:has-text("Analyze")');
    if (submitBtn) {
      const isDisabled = await submitBtn.evaluate(el => el.disabled);
      if (!isDisabled) {
        await submitBtn.click();
        log(PASS, 'Analyze button clicked');

        // Wait for loading state
        await page.waitForTimeout(2000);
        const loadingIndicator = await page.$('[class*="loading"], [class*="spinner"], [class*="analyzing"]');
        log(loadingIndicator ? PASS : WARN, 'Loading state visible after submit');

        // Wait for results (up to 30s)
        try {
          await page.waitForFunction(() => {
            const body = document.body.innerText;
            return body.includes('SEO Score') || body.includes('score') || body.includes('Title') || body.includes('Error');
          }, { timeout: 45000 });
          const resultText = await page.innerText('body');
          const hasScore = /score|SEO Score|title tag|meta/i.test(resultText);
          log(hasScore ? PASS : WARN, 'Results rendered in UI');
        } catch {
          log(WARN, 'Results did not appear within 45s (rate limit or slow API)');
        }
      } else {
        log(WARN, 'Submit button is disabled');
      }
    } else {
      log(WARN, 'No submit button found');
    }
  } else {
    log(FAIL, 'URL input not found on page');
  }

  // ─── 8. NETWORK RESPONSE AUDIT ──────────────────────────
  section('8 · API Network Response Audit');
  const apiResponses = networkResponses.filter(r => r.url.includes('railway.app') || r.url.includes('localhost'));

  if (apiResponses.length === 0) {
    log(WARN, 'No API JSON responses captured (may not have completed analysis)');
  } else {
    for (const resp of apiResponses) {
      const path = new URL(resp.url).pathname;
      log(PASS, `API response received`, `${path} → HTTP ${resp.status}`);

      // Check for server-side key leaks in API responses
      for (const { label, re } of FORBIDDEN_PATTERNS) {
        if (re.test(resp.body)) {
          log(FAIL, `Secret in API response!`, `${label} in ${path}`);
        }
      }

      // Check for excessive data (raw DB records, internal fields)
      const excessive = ['_id', '__v', 'password', 'token', 'secret', 'private_key', 'connection_string'];
      for (const field of excessive) {
        if (resp.body.includes(`"${field}"`)) {
          log(FAIL, `Sensitive field in API response`, `"${field}" in ${path}`);
        }
      }
    }
  }

  // ─── 9. CONTACT FORM ────────────────────────────────────
  section('9 · Contact Form Flow');
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(500);

  const contactBtn = await page.$('button:has-text("Contact"), a:has-text("Contact")');
  if (contactBtn) {
    await contactBtn.click();
    await page.waitForTimeout(1000);

    const form = await page.$('form:has(textarea)');
    if (form) {
      log(PASS, 'Contact modal opened');
      await form.$('input[type="text"]').then(el => el?.fill('Security Auditor'));
      await form.$('input[type="email"]').then(el => el?.fill('auditor@example.com'));
      await form.$('textarea').then(el => el?.fill('E2E audit test submission — please ignore.'));
      log(PASS, 'Contact form fields filled');

      // Don't actually submit — just verify form is functional
      const submitBtn = await form.$('button[type="submit"]');
      const isEnabled = submitBtn ? !(await submitBtn.evaluate(el => el.disabled)) : false;
      log(isEnabled ? PASS : WARN, 'Contact form submit button enabled');

      // Close modal
      const closeBtn = await page.$('[aria-label="close"], button:has-text("×"), button:has-text("✕")');
      if (closeBtn) await closeBtn.click().catch(() => {});
    } else {
      log(WARN, 'Contact modal did not open or form not found');
    }
  } else {
    log(WARN, 'Contact button not found in footer');
  }

  // ─── 10. LEGAL LINKS ────────────────────────────────────
  section('10 · Legal & Compliance Links');
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(500);

  const legalItems = ['Terms of Service', 'Privacy Policy', 'Cookie Policy'];
  for (const label of legalItems) {
    const btn = await page.$(`button:has-text("${label}"), a:has-text("${label}")`);
    if (btn) {
      await btn.click({ force: true });
      await page.waitForTimeout(800);
      const text = await page.innerText('body');
      const hasContent = text.includes(label) && text.length > 500;
      log(hasContent ? PASS : FAIL, `${label} modal opens with content`);
      await page.keyboard.press('Escape');
      await page.waitForTimeout(400);
    } else {
      log(WARN, `${label} link not found`);
    }
  }

  // ─── 11. SECURITY HEADERS CHECK ─────────────────────────
  section('11 · HTTP Security Headers');
  // Use a unique path to bypass CDN edge cache and hit the Worker directly
  const resp = await page.request.get(`${TARGET}/nocache-${Date.now()}`);
  const headers = resp.headers();

  const secHeaders = [
    ['x-content-type-options', 'nosniff'],
    ['x-frame-options', null],
    ['referrer-policy', null],
  ];
  for (const [header, expected] of secHeaders) {
    const val = headers[header];
    if (!val) {
      log(WARN, `Missing header`, header);
    } else if (expected && val !== expected) {
      log(WARN, `Header value unexpected`, `${header}: ${val}`);
    } else {
      log(PASS, `Header present`, `${header}: ${val}`);
    }
  }

  // CSP
  const csp = headers['content-security-policy'];
  log(csp ? PASS : WARN, csp ? 'CSP header present' : 'No Content-Security-Policy header (consider adding)');

  // ─── 12. SENSITIVE COMMENT SCAN IN RENDERED HTML ────────
  section('12 · HTML Comment & Hidden Field Scan');
  const comments = await page.evaluate(() => {
    const walker = document.createTreeWalker(document, NodeFilter.SHOW_COMMENT);
    const found = [];
    let node;
    while ((node = walker.nextNode())) found.push(node.textContent.trim());
    return found;
  });

  if (comments.length === 0) {
    log(PASS, 'No HTML comments in rendered DOM');
  } else {
    for (const c of comments) {
      const suspicious = /key|secret|password|token|api|todo|fixme|hack|debug/i.test(c);
      log(suspicious ? FAIL : WARN, `HTML comment found`, c.substring(0, 80));
    }
  }

  const hiddenInputs = await page.$$('input[type="hidden"]');
  if (hiddenInputs.length === 0) {
    log(PASS, 'No hidden input fields');
  } else {
    for (const input of hiddenInputs) {
      const name = await input.getAttribute('name');
      const value = await input.getAttribute('value');
      log(WARN, `Hidden input`, `name="${name}" value="${String(value).substring(0, 40)}"`);
    }
  }

  // ─── FINAL REPORT ───────────────────────────────────────
  console.log(`\n${'═'.repeat(60)}`);
  console.log(` AUDIT COMPLETE`);
  console.log(`${'═'.repeat(60)}`);
  console.log(`  ${PASS} Passed : ${passed}`);
  console.log(`  ${WARN} Warned : ${warned}`);
  console.log(`  ${FAIL} Failed : ${failed}`);
  console.log(`${'═'.repeat(60)}\n`);

  await browser.close();
  process.exit(failed > 0 ? 1 : 0);
})();
