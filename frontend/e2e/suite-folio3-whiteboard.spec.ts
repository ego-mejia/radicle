import { readFile } from 'node:fs/promises';
import { expect, test, type Browser, type Page } from '@playwright/test';

/**
 * Folio 3.5, whiteboards: two people draw on the same whiteboard at once, each canvas
 * gets the other's drawing, it exports to SVG, and it goes inside a page from the `/`
 * menu. Runs after suite.spec.ts on the same instance (it signs in as its admin).
 */
test.describe.configure({ mode: 'serial' });

const ADMIN = { email: 'fernando@example.com', password: 'e2e-password-1' };
const ANA = {
  handle: 'ana-wb',
  name: 'Ana Pizarra',
  email: 'ana-wb@example.com',
  password: 'e2e-wb-1',
};
const METADATA = {
  description: 'La arquitectura de pagos, dibujada entre dos en un whiteboard.',
  doc_type: 'how-to',
  labels: ['arquitectura'],
  owner: '@fernando',
  audiences: ['everyone'],
  language: 'es',
};
let admin: Page;
let ana: Page;
let boardUrl = '';
let boardId = '';

type Element = { type: string; text?: string; isDeleted?: boolean };

async function signIn(browser: Browser, who: { email: string; password: string }) {
  const page = await (await browser.newContext({ acceptDownloads: true })).newPage();
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

/** Drags on the canvas with a toolbar tool, from one point to another. */
async function draw(page: Page, tool: string, from: [number, number], to: [number, number]) {
  await page.bringToFront();
  const canvas = page.locator('canvas.interactive');
  const box = (await canvas.boundingBox())!;
  // Excalidraw's tool buttons are radio inputs styled away behind their icons.
  await page.getByTestId(`toolbar-${tool}`).click({ force: true });
  await page.mouse.move(box.x + from[0], box.y + from[1]);
  await page.mouse.down();
  await page.mouse.move(box.x + to[0], box.y + to[1], { steps: 8 });
  await page.mouse.up();
}

async function write(page: Page, at: [number, number], text: string) {
  await page.bringToFront();
  const box = (await page.locator('canvas.interactive').boundingBox())!;
  await page.getByTestId('toolbar-text').click({ force: true });
  await page.mouse.click(box.x + at[0], box.y + at[1]);
  await page.keyboard.type(text);
  await page.keyboard.press('Escape');
}

async function scene() {
  const board = await api<{ elements: Element[] }>('GET', `/folio/whiteboards/${boardId}`);
  return board.elements.filter((e) => !e.isDeleted);
}

test.beforeAll(async ({ browser }) => {
  admin = await signIn(browser, ADMIN);
  await api('POST', '/folio/spaces', { key: 'e2e-wb', name: 'E2E Whiteboards' });
  await api('POST', '/users', {
    handle: ANA.handle,
    display_name: ANA.name,
    email: ANA.email,
    password: ANA.password,
  });
  await api('POST', '/folio/admin/grants', {
    grantee_type: 'user',
    grantee: ANA.handle,
    role: 'creator',
  });
  const grants = await api<{ grants: unknown[] }>('GET', '/folio/spaces/e2e-wb/grants');
  await api('PUT', '/folio/spaces/e2e-wb/grants', {
    grants: [
      ...grants.grants,
      { grantee_type: 'user', grantee: ANA.handle, permissions: ['view', 'create'] },
    ],
  });
  ana = await signIn(browser, ANA);
});

test('create a whiteboard and land on its canvas', async () => {
  // Creating kinds other than a page lives in Manage › Pages (RAD-57).
  await admin.goto('/folio/s/e2e-wb/admin');
  await admin.getByRole('button', { name: 'New whiteboard' }).click();
  const dialog = admin.getByRole('dialog', { name: 'New whiteboard' });
  await dialog.getByLabel('Title').fill('Arquitectura de pagos');
  await dialog.getByRole('button', { name: 'Create' }).click();
  await expect(admin.getByRole('heading', { name: 'Arquitectura de pagos' })).toBeVisible();
  await expect(admin.locator('canvas.interactive')).toBeVisible();
  boardUrl = admin.url();
  boardId = new URL(boardUrl).pathname.split('/').pop()!.slice(0, 36);
});

test('two people draw at once and each canvas gets the other drawing', async () => {
  await ana.goto(boardUrl);
  await expect(ana.locator('canvas.interactive')).toBeVisible();
  for (const p of [admin, ana])
    await expect(p.getByLabel('1 person in this document')).toBeVisible();

  // Right of the style panel that opens on the left with a tool.
  await draw(admin, 'rectangle', [350, 320], [520, 410]);
  await write(ana, [520, 220], 'Servicio de pagos');
  await expect
    .poll(async () => (await scene()).map((e) => e.text ?? e.type).sort())
    .toEqual(['Servicio de pagos', 'rectangle']);

  // Fernando's export has Ana's text: it reached his canvas.
  const download = admin.waitForEvent('download');
  await admin.getByRole('button', { name: 'SVG' }).click();
  const svg = await readFile((await (await download).path())!, 'utf8');
  expect(svg).toContain('<svg');
  expect(svg).toContain('Servicio de pagos');
});

test('it is found by search', async () => {
  await expect
    .poll(async () => {
      const r = await api<{ items: { node_id: string }[] }>(
        'GET',
        '/folio/search?q=servicio%20de%20pagos&mode=text',
      );
      return r.items.map((i) => i.node_id);
    })
    .toContain(boardId);
});

test('it goes inside a page from the / menu and readers see it there', async () => {
  const node = await api<{ id: string; slug: string }>('POST', '/folio/nodes', {
    space: 'e2e-wb',
    kind: 'page',
    title: 'Pagos, visto desde arriba',
  });
  await admin.goto(`/folio/p/${node.id}-${node.slug}/edit`);
  await admin.locator('.ProseMirror').click();
  await admin.keyboard.type('/whiteboard');
  await admin.keyboard.press('Enter');
  await admin.getByRole('combobox', { name: 'Choose a whiteboard' }).selectOption({
    label: 'Arquitectura de pagos',
  });
  // The room saves the draft every few seconds.
  const draft = () => api<{ content_md: string }>('GET', `/folio/nodes/${node.id}/draft`);
  await expect
    .poll(async () => (await draft()).content_md, { timeout: 15_000 })
    .toContain(`::whiteboard{id=${boardId}}`);
  await api('PUT', `/folio/nodes/${node.id}/draft`, {
    content_md: (await draft()).content_md,
    metadata: METADATA,
  });
  await api('POST', `/folio/nodes/${node.id}/publish`, {});

  await ana.goto(`/folio/p/${node.id}-${node.slug}`);
  // Exact: the page's pager also links to it as "Previous Arquitectura de pagos".
  await expect(ana.getByRole('link', { name: 'Arquitectura de pagos', exact: true })).toBeVisible();
  await expect(ana.locator('.excalidraw')).toBeVisible();
  await expect(ana.getByText("You can't see this whiteboard.")).toHaveCount(0);
});
