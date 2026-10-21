import { expect, test, type Page } from '@playwright/test';

/**
 * Folio phase 1, end to end: a person writes a page in the editor and publishes it with
 * its metadata, reads it and finds it in search; an agent's post waits in the approval
 * queue until an admin approves it. Runs after suite.spec.ts on the same instance.
 */
test.describe.configure({ mode: 'serial' });

const ADMIN = { email: 'fernando@example.com', password: 'e2e-password-1' };
let page: Page;

async function api<T = unknown>(method: string, url: string, body?: unknown, token?: string) {
  return page.evaluate(
    async ({ method, url, body, token }) => {
      const csrf = document.cookie.match(/radicle_csrf=([^;]+)/)?.[1] ?? '';
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers.Authorization = `Bearer ${token}`;
      else headers['X-CSRF-Token'] = csrf;
      const r = await fetch(`/api/v1${url}`, {
        method,
        headers,
        credentials: token ? 'omit' : 'same-origin',
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const text = await r.text();
      if (!r.ok) throw new Error(`${method} ${url}: ${r.status} ${text}`);
      return (text ? JSON.parse(text) : null) as T;
    },
    { method, url, body, token },
  );
}

test.beforeAll(async ({ browser }) => {
  page = await (await browser.newContext()).newPage();
  await page.goto('/login');
  await page.getByLabel('Email').fill(ADMIN.email);
  await page.getByLabel('Password').fill(ADMIN.password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible();
  await api('POST', '/folio/spaces', { key: 'e2e-docs', name: 'E2E Docs' });
});

test('write a page, publish it with its metadata and read it', async () => {
  await page.goto('/folio');
  await page.getByRole('button', { name: 'Write' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByLabel('Space').selectOption({ label: 'E2E Docs' });
  await dialog.getByLabel('Title').fill('Guía de despliegue E2E');
  await dialog.getByRole('button', { name: 'Start writing' }).click();

  await expect(page).toHaveURL(/\/edit$/);
  const body = page.locator('.ProseMirror');
  await body.click();
  await page.keyboard.type('# Requisitos');
  await page.keyboard.press('Enter');
  await page.keyboard.type('Docker 24 y dos gigas de memoria para el despliegue.');
  await expect(page.getByRole('status').filter({ hasText: /^Saved$/ })).toBeVisible();

  await page.getByRole('button', { name: 'Publish' }).click();
  const publish = page.getByRole('dialog', { name: 'Publish' });
  await publish
    .getByLabel('Description')
    .fill('Cómo desplegar Radicle en un servidor propio, paso a paso.');
  await publish.getByLabel('Document type').selectOption({ index: 1 });
  await publish.getByLabel('Language').selectOption({ index: 1 });
  await publish.getByLabel('Labels').fill('deploy, e2e');
  await publish.getByLabel('Owner').fill('fernando');
  await publish.getByRole('checkbox').first().check();
  await publish.getByRole('button', { name: 'Publish' }).click();

  await expect(
    page.getByRole('heading', { name: 'Guía de despliegue E2E', level: 1 }),
  ).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Requisitos' })).toBeVisible();
  await expect(page.getByText('#deploy')).toBeVisible();
});

test('the topbar search finds it by its section', async () => {
  await page.goto('/folio');
  const search = page.getByRole('combobox', { name: 'Search the docs' });
  await expect(async () => {
    await search.fill('');
    await search.fill('requisitos despliegue');
    await expect(page.getByRole('option', { name: /Guía de despliegue E2E/ })).toBeVisible({
      timeout: 2_000,
    });
  }).toPass({ timeout: 30_000 }); // the index catches up within seconds
  await page.getByRole('option', { name: /Guía de despliegue E2E/ }).click();
  await expect(page).toHaveURL(/#requisitos$/);
});

test("an agent's post waits for approval, then goes live", async () => {
  const agent = await api<{ token: { token: string } | string }>('POST', '/agents', {
    handle: 'agente-e2e',
    display_name: 'Agente E2E',
  });
  const token = typeof agent.token === 'string' ? agent.token : agent.token.token;
  await api('POST', '/folio/admin/grants', {
    grantee_type: 'user',
    grantee: 'agente-e2e',
    role: 'creator',
  });
  const grants = await api<{ grants: unknown[] }>('GET', '/folio/spaces/e2e-docs/grants');
  await api('PUT', '/folio/spaces/e2e-docs/grants', {
    grants: [
      ...grants.grants,
      { grantee_type: 'user', grantee: 'agente-e2e', permissions: ['view', 'create'] },
    ],
  });
  const node = await api<{ id: string }>(
    'POST',
    '/folio/nodes',
    { space: 'e2e-docs', kind: 'blog_post', title: 'Resumen semanal E2E' },
    token,
  );
  await api(
    'PUT',
    `/folio/nodes/${node.id}/draft`,
    {
      content_md: '# Lo nuevo\n\nBúsqueda híbrida y cola de aprobación.',
      metadata: {
        description: 'Lo que cambió esta semana en el repositorio, resumido por el agente.',
        doc_type: 'how-to',
        labels: ['changelog'],
        owner: '@fernando',
        audiences: ['everyone'],
        language: 'es',
      },
    },
    token,
  );
  await api('POST', `/folio/nodes/${node.id}/publish`, { change_note: 'Desde el repo' }, token);

  await page.goto('/folio/approvals');
  await page.getByRole('button', { name: /Resumen semanal E2E/ }).click();
  await page.getByRole('button', { name: 'Approve' }).click();
  await expect(page.getByText('Published as v1')).toBeVisible();
  await page.goto(`/folio/p/${node.id}`);
  await expect(page.getByRole('heading', { name: 'Resumen semanal E2E', level: 1 })).toBeVisible();
});
