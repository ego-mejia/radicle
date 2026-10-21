import { expect, test, type Browser, type Page } from '@playwright/test';

/**
 * Folio phase 0: one sign-in for both apps, the suite switch in the logo, `g f` / `g d`,
 * and Folio hidden for someone without a Folio role. Runs after the stage specs on the
 * same instance (the admin and the PA project exist).
 */
test.describe.configure({ mode: 'serial' });

const ADMIN = { email: 'fernando@example.com', password: 'e2e-password-1' };
const OUTSIDER = { handle: 'teo', email: 'teo@example.com', password: 'e2e-password-9' };
let page: Page;

async function signIn(browser: Browser, who: { email: string; password: string }) {
  const p = await (await browser.newContext()).newPage();
  await p.goto('/login');
  await p.getByLabel('Email').fill(who.email);
  await p.getByLabel('Password').fill(who.password);
  await p.getByRole('button', { name: 'Sign in' }).click();
  await expect(p.getByRole('heading', { name: 'Projects' })).toBeVisible();
  return p;
}

async function api<T = unknown>(
  method: string,
  url: string,
  body?: unknown,
  ok: number[] = [],
): Promise<T> {
  return page.evaluate(
    async ({ method, url, body, ok }) => {
      const csrf = document.cookie.match(/radicle_csrf=([^;]+)/)?.[1] ?? '';
      const r = await fetch(`/api/v1${url}`, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const text = await r.text();
      if (!r.ok && !ok.includes(r.status)) throw new Error(`${method} ${url}: ${r.status} ${text}`);
      return text && r.ok ? JSON.parse(text) : null;
    },
    { method, url, body, ok },
  );
}

test.beforeAll(async ({ browser }) => {
  page = await signIn(browser, ADMIN);
});

test('switch to Folio from the logo and back without signing in again', async () => {
  await page.goto('/p/PA/board');
  await page.getByRole('button', { name: /Switch app, now Radicle Docket/ }).click();
  await page.getByRole('menuitem', { name: /Radicle Folio/ }).click();
  await expect(page).toHaveURL(/\/folio$/);
  await expect(page.getByRole('heading', { name: 'Home', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /Switch app, now Radicle Folio/ })).toBeVisible();

  // g d goes back to where Docket was left; g f returns to Folio.
  await page.keyboard.press('g');
  await page.keyboard.press('d');
  await expect(page).toHaveURL(/\/p\/PA\/board/);
  await page.keyboard.press('g');
  await page.keyboard.press('f');
  await expect(page).toHaveURL(/\/folio$/);
  await expect(page.getByRole('heading', { name: 'Home', exact: true })).toBeVisible();
});

test('a Folio admin gives a group the creator role', async () => {
  await api('POST', '/groups', { name: 'equipo-docs-e2e' }, [409]);
  await page.goto('/folio/admin');
  await expect(page.getByRole('heading', { name: 'Folio admin' })).toBeVisible();
  await page.getByLabel('Group').fill('equipo-docs-e2e');
  await page.getByRole('combobox', { name: 'Role', exact: true }).selectOption('creator');
  await page.getByRole('button', { name: 'Add' }).click();
  await expect(page.getByRole('combobox', { name: 'Role of equipo-docs-e2e' })).toHaveValue(
    'creator',
  );
});

test('without a Folio role, Folio is not in the switch', async ({ browser }) => {
  await api(
    'POST',
    '/users',
    {
      handle: OUTSIDER.handle,
      display_name: 'Teo',
      email: OUTSIDER.email,
      password: OUTSIDER.password,
    },
    [409],
  );
  const grants = await api<{ items: { id: string; grantee_type: string }[] }>(
    'GET',
    '/folio/admin/grants',
  );
  const everyone = grants.items.find((g) => g.grantee_type === 'everyone');
  if (everyone) await api('DELETE', `/folio/admin/grants/${everyone.id}`);
  try {
    const teo = await signIn(browser, OUTSIDER);
    await teo.getByRole('button', { name: /Switch app/ }).click();
    await expect(teo.getByRole('menuitem', { name: /Radicle Docket/ })).toBeVisible();
    await expect(teo.getByRole('menuitem', { name: /Radicle Folio/ })).toHaveCount(0);
    await teo.keyboard.press('Escape');
    await teo.goto('/folio');
    await expect(teo.getByRole('heading', { name: 'Projects' })).toBeVisible();
  } finally {
    await api('POST', '/folio/admin/grants', { grantee_type: 'everyone', role: 'reader' });
  }
});
