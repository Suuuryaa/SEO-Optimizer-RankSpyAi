const { defineConfig } = require('@playwright/test')

module.exports = defineConfig({
  testMatch: '**/*.test.js',
  timeout: 120000,
  retries: 1,
  workers: 1, // Sequential — backend has rate limits
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  use: {
    baseURL: 'https://rankspyseo.xyz',
    headless: true,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'retain-on-failure',
    actionTimeout: 15000,
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
})
