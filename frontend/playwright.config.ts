import { defineConfig, devices } from '@playwright/test';

/**
 * End-to-end tests run against a real Radicle with a fresh database. The specs sign in
 * more than the login limit allows in a minute, so raise it for the run:
 *   docker compose down -v
 *   RADICLE_LOGIN_RATE_LIMIT_PER_MINUTE=100 docker compose up -d --build && pnpm e2e
 * RADICLE_E2E_URL points elsewhere; PLAYWRIGHT_CHANNEL=chrome uses the local Chrome.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: process.env.RADICLE_E2E_URL ?? 'http://localhost:8000',
    locale: 'en-US',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    permissions: ['clipboard-read', 'clipboard-write'],
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], channel: process.env.PLAYWRIGHT_CHANNEL || undefined },
    },
  ],
});
