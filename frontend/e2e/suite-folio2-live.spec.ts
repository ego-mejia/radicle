import { expect, test, type Browser, type Page } from '@playwright/test';

/**
 * Folio phase 2, real time: three people write the same live doc at once, each sees the
 * others' text, carets and mouse pointers, and the doc keeps no publish button. Runs after
 * suite.spec.ts on the same instance (it signs in as its admin).
 */
test.describe.configure({ mode: 'serial' });

const ADMIN = { email: 'fernando@example.com', password: 'e2e-password-1' };
const PEOPLE = [
  { handle: 'ana-live', name: 'Ana Live', email: 'ana-live@example.com', password: 'e2e-live-1' },
  {
    handle: 'beto-live',
    name: 'Beto Live',
    email: 'beto-live@example.com',
    password: 'e2e-live-2',
  },
];
let admin: Page;
let others: Page[] = [];
let docUrl = '';

async function signIn(browser: Browser, who: { email: string; password: string }) {
  const page = await (await browser.newContext()).newPage();
  await page.goto('/login');
  await page.getByLabel('Email').fill(who.email);
  await page.getByLabel('Password').fill(who.password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.waitForURL((u) => !u.pathname.startsWith('/login'));
  return page;
}

async function api<T = unknown>(method: string, url: string, body?: unknown) {
  return admin.evaluate(
    async ({ method, url, body }) => {
      const csrf = document.cookie.match(/radicle_csrf=([^;]+)/)?.[1] ?? '';
      const r = await fetch(`/api/v1${url}`, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const text = await r.text();
      if (!r.ok) throw new Error(`${method} ${url}: ${r.status} ${text}`);
      return (text ? JSON.parse(text) : null) as T;
    },
    { method, url, body },
  );
}

/** The doc's text without the others' caret labels, which sit inside it. */
function docText(page: Page) {
  return page.locator('.ProseMirror').evaluate((el) => {
    const copy = el.cloneNode(true) as HTMLElement;
    copy.querySelectorAll('.collaboration-carets__caret').forEach((c) => c.remove());
    return copy.textContent ?? '';
  });
}

/** Writes a line at the end of the doc. */
async function writeLine(page: Page, text: string) {
  await page.bringToFront();
  await page.locator('.ProseMirror > *').last().click();
  // ProseMirror reads the click's selection on the next selectionchange.
  await page.waitForTimeout(100);
  await page.keyboard.press('End');
  await page.keyboard.press('Enter');
  await page.keyboard.type(text);
}

test.beforeAll(async ({ browser }) => {
  admin = await signIn(browser, ADMIN);
  await api('POST', '/folio/spaces', { key: 'e2e-live', name: 'E2E Live' });
  for (const p of PEOPLE) {
    await api('POST', '/users', {
      handle: p.handle,
      display_name: p.name,
      email: p.email,
      password: p.password,
    });
    await api('POST', '/folio/admin/grants', {
      grantee_type: 'user',
      grantee: p.handle,
      role: 'creator',
    });
  }
  const grants = await api<{ grants: unknown[] }>('GET', '/folio/spaces/e2e-live/grants');
  await api('PUT', '/folio/spaces/e2e-live/grants', {
    grants: [
      ...grants.grants,
      ...PEOPLE.map((p) => ({
        grantee_type: 'user',
        grantee: p.handle,
        permissions: ['view', 'create'],
      })),
    ],
  });
  others = await Promise.all(PEOPLE.map((p) => signIn(browser, p)));
});

test('create a live doc and land in the shared editor', async () => {
  // Creating kinds other than a page lives in Manage › Pages (RAD-57).
  await admin.goto('/folio/s/e2e-live/admin');
  await admin.getByRole('button', { name: 'New live doc' }).click();
  const dialog = admin.getByRole('dialog', { name: 'New live doc' });
  await dialog.getByLabel('Title').fill('Minuta en vivo');
  await dialog.getByRole('button', { name: 'Create' }).click();
  await expect(admin).toHaveURL(/\/edit$/);
  docUrl = admin.url().replace(/\/edit$/, '');
  await expect(admin.getByRole('button', { name: 'Publish' })).toHaveCount(0);
  await writeLine(admin, 'Agenda de Fernando');
});

test('three people write at once and see each other', async () => {
  // Opening the doc's page takes editors straight into the editor.
  await Promise.all(others.map((p) => p.goto(docUrl)));
  for (const p of others) {
    await expect(p).toHaveURL(/\/edit$/);
    await expect.poll(() => docText(p)).toContain('Agenda de Fernando');
  }
  const all = [admin, ...others];
  // Each sees the two others.
  for (const p of all) await expect(p.getByLabel('2 people in this document')).toBeVisible();

  await writeLine(others[0]!, 'Punto de Ana');
  await writeLine(others[1]!, 'Punto de Beto');
  for (const p of all) {
    await expect.poll(() => docText(p)).toContain('Punto de Ana');
    await expect.poll(() => docText(p)).toContain('Punto de Beto');
  }

  // Everyone's mouse over the page, with their name, and their carets in the text.
  for (const [i, p] of all.entries()) await p.mouse.move(500 + i * 40, 300 + i * 20);
  await expect(admin.getByTestId('pointer')).toHaveCount(2);
  await expect(admin.getByTestId('pointer').filter({ hasText: 'Ana Live' })).toBeVisible();
  await expect(others[0]!.getByTestId('pointer').filter({ hasText: 'Beto Live' })).toBeVisible();
  await expect(admin.locator('.collaboration-carets__label')).toHaveCount(2);
});

test('the doc keeps what everyone wrote, and has its snapshots page', async () => {
  await admin.reload();
  await expect.poll(() => docText(admin)).toContain('Punto de Beto');
  await admin.getByRole('link', { name: 'Snapshots' }).click();
  await expect(admin.getByRole('heading', { name: 'Snapshots' })).toBeVisible();
});
