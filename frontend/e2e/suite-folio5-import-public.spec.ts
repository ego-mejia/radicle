import { fileURLToPath } from 'node:url';
import { expect, test, type Browser, type Page } from '@playwright/test';

/**
 * Folio phase 5, end to end: a Confluence space comes in through the import wizard,
 * importing it again updates instead of duplicating, one of its pages is published and
 * shared with a public link that opens without an account, and revoking the link makes it
 * a 404. (The Slack notice on publishing is covered by the backend tests: a local
 * receiver is a private address, which Radicle refuses to call.) Runs after suite.spec.ts
 * on the same instance (it signs in as its admin).
 */
test.describe.configure({ mode: 'serial' });

const ADMIN = { email: 'fernando@example.com', password: 'e2e-password-1' };
// The backend's sample export (backend/tests/fixtures/folio_import/confluence), zipped.
const EXPORT = fileURLToPath(new URL('./fixtures/confluence-eng.zip', import.meta.url));
const METADATA = {
  description: 'Cómo conectar un agente de Claude a Radicle, traído desde Confluence.',
  doc_type: 'how-to',
  labels: ['mcp'],
  owner: '@fernando',
  audiences: ['everyone'],
  language: 'es',
};
let admin: Page;
let pageId = '';
let publicUrl = '';

async function signIn(browser: Browser) {
  const page = await (await browser.newContext()).newPage();
  await page.goto('/login');
  await page.getByLabel('Email').fill(ADMIN.email);
  await page.getByLabel('Password').fill(ADMIN.password);
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

async function importOnce(round: number) {
  await admin.goto('/folio/admin');
  await admin.getByRole('tab', { name: 'Import' }).click();
  await admin.getByLabel('Into the space').selectOption('conf');
  await admin.locator('input[type=file]').setInputFiles(EXPORT);
  await admin.getByRole('button', { name: 'Upload and check' }).click();
  await expect(admin.getByText('What will happen')).toBeVisible({ timeout: 30_000 });
  const action = round === 1 ? 'New' : 'Update';
  await expect(admin.getByText(action, { exact: true })).toHaveCount(4);
  await admin.getByRole('button', { name: 'Import 4 pages' }).click();
  await expect(admin.getByText('Imported', { exact: true })).toBeVisible({ timeout: 60_000 });
}

test.beforeAll(async ({ browser }) => {
  admin = await signIn(browser);
  await api('POST', '/folio/spaces', { key: 'conf', name: 'Confluence' });
});

test('a Confluence space comes in, and importing it again does not duplicate it', async () => {
  await importOnce(1);
  await importOnce(2);
  type Node = { id: string; title: string; children: Node[] };
  const tree = await api<Node[]>('GET', '/folio/spaces/conf/tree');
  const titles: string[] = [];
  const walk = (nodes: Node[]) =>
    nodes.forEach((n) => {
      titles.push(n.title);
      if (n.title === 'Conectar un agente') pageId = n.id;
      walk(n.children ?? []);
    });
  walk(tree);
  expect(titles.sort()).toEqual(['Conectar un agente', 'Decisiones', 'Guías', 'Home']);
});

test('a public link opens without an account, and is gone once revoked', async ({ browser }) => {
  const draft = await api<{ content_md: string }>('GET', `/folio/nodes/${pageId}/draft`);
  await api('PUT', `/folio/nodes/${pageId}/draft`, {
    content_md: draft.content_md,
    metadata: METADATA,
  });
  await api('POST', `/folio/nodes/${pageId}/publish`, { change_note: 'Importada' });

  await admin.goto(`/folio/p/${pageId}`);
  await admin.getByRole('button', { name: 'Share' }).click();
  await admin.getByRole('tab', { name: 'Public link' }).click();
  await admin.getByRole('button', { name: 'Create link' }).first().click();
  const field = admin.getByLabel('Public link').first();
  await expect(field).toHaveValue(/\/pub\//);
  publicUrl = await field.inputValue();

  const stranger = await (await browser.newContext()).newPage();
  const opened = await stranger.goto(publicUrl);
  expect(opened?.status()).toBe(200);
  expect(opened?.headers()['x-robots-tag']).toContain('noindex');
  await expect(stranger.getByRole('heading', { name: 'Conectar un agente' })).toBeVisible();
  await expect(stranger.getByRole('button', { name: 'Sign in' })).toHaveCount(0);

  await admin.getByRole('button', { name: 'Revoke' }).first().click();
  await expect(admin.getByText('Link revoked: it no longer opens.')).toBeVisible();
  const gone = await stranger.goto(publicUrl);
  expect(gone?.status()).toBe(404);
});
