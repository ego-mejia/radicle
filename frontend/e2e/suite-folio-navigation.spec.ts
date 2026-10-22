import type { Server } from 'node:http';
import { expect, test, type Page } from '@playwright/test';
// @ts-expect-error a plain .mjs helper, also runnable on its own with node
import { startFakeAi } from './fixtures/fake-ai.mjs';

/**
 * RAD-57, Folio's navigation: the suite switch stays put between Docket and Folio, the
 * fixed sidebar opens a space on its portada, and the sections (Specs, Architecture
 * decisions, Guides) filter and lead to pages whose path goes back. Manage opens the
 * space's admin mode, and Radi answers in Folio. Runs after suite.spec.ts on the same
 * instance (it signs in as its admin); the Radi test needs the fake model (see
 * suite-folio4-docket-ai.spec.ts).
 */
test.describe.configure({ mode: 'serial' });

const ADMIN = { email: 'fernando@example.com', password: 'e2e-password-1' };
const FAKE_AI_PORT = 8791;
const FAKE_AI =
  process.env.RADICLE_E2E_FAKE_AI_URL ??
  (process.env.CI ? '' : `http://host.docker.internal:${FAKE_AI_PORT}/v1`);
const META = { owner: '@fernando', audiences: ['everyone'], language: 'es', labels: ['equipo'] };
// A fresh space per run, so a rerun against the same instance starts clean.
const RUN = Date.now().toString(36).slice(-5);
const SPACE = { key: `nav${RUN}`, name: `Navegación ${RUN}` };

let admin: Page;
let fakeAi: Server | undefined;

async function api<T = unknown>(method: string, url: string, body?: unknown, ok409 = false) {
  return admin.evaluate(
    async ({ method, url, body, ok409 }) => {
      const csrf = document.cookie.match(/radicle_csrf=([^;]+)/)?.[1] ?? '';
      const r = await fetch(`/api/v1${url}`, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const text = await r.text();
      if (!r.ok && !(ok409 && r.status === 409)) {
        throw new Error(`${method} ${url}: ${r.status} ${text}`);
      }
      return (text ? JSON.parse(text) : null) as T;
    },
    { method, url, body, ok409 },
  );
}

async function page(title: string, meta: Record<string, unknown>, parent?: string) {
  const node = await api<{ id: string }>('POST', '/folio/nodes', {
    space: SPACE.key,
    kind: 'page',
    title,
    parent: parent ?? null,
  });
  await api('PUT', `/folio/nodes/${node.id}/draft`, {
    content_md: `## Contexto\n\n${meta.description}\n\n## Detalle\n\nCómo se hace, paso a paso.\n`,
    // Descriptions need 40 to 400 characters.
    metadata: { ...META, ...meta, description: `${meta.description} Escrita por el equipo.` },
  });
  await api('POST', `/folio/nodes/${node.id}/publish`, { change_note: 'Primera versión' });
  return node.id;
}

test.beforeAll(async ({ browser }) => {
  admin = await (await browser.newContext()).newPage();
  await admin.goto('/login');
  await admin.getByLabel('Email').fill(ADMIN.email);
  await admin.getByLabel('Password').fill(ADMIN.password);
  await admin.getByRole('button', { name: 'Sign in' }).click();
  await admin.waitForURL((u) => !u.pathname.startsWith('/login'));

  await api('POST', '/folio/spaces', {
    ...SPACE,
    description: 'Specs, decisiones y guías del equipo.',
  });
  await api('POST', '/projects', { key: 'NV', name: 'Navegación' }, true);
  for (const area of ['Pagos', 'Envíos']) {
    await api('POST', '/projects/NV/areas', { name: area }, true);
  }
  await page('Etapa 1: pagos', {
    doc_type: 'build-spec',
    description: 'Cobrar con tarjeta y transferencia desde la tienda.',
    docket_project: 'NV',
    docket_areas: ['Pagos'],
  });
  await page('Etapa 2: envíos', {
    doc_type: 'build-spec',
    description: 'Calcular y rastrear los envíos de cada pedido.',
    docket_project: 'NV',
    docket_areas: ['Envíos'],
  });
  const old = await page('Búsqueda solo de texto', {
    doc_type: 'decision-log',
    description: 'La primera búsqueda usaba solo el índice de texto.',
    decision_topic: 'Datos',
  });
  await page('Búsqueda híbrida con pgvector', {
    doc_type: 'decision-log',
    description: 'Embeddings en Postgres, fusionados con el texto.',
    decision_topic: 'Datos',
    decision_replaces: old,
  });
  const folder = await api<{ id: string }>('POST', '/folio/nodes', {
    space: SPACE.key,
    kind: 'folder',
    title: 'Primeros pasos',
  });
  await page(
    'Levanta la tienda en local',
    {
      doc_type: 'how-to',
      description: 'Docker, base de datos y datos de ejemplo.',
      labels: ['getting-started'],
    },
    folder.id,
  );
  await page(
    'Tu primer cambio',
    {
      doc_type: 'how-to',
      description: 'Ramas, revisiones y cómo se publica.',
      labels: ['getting-started'],
    },
    folder.id,
  );
});

test.afterAll(async () => {
  if (fakeAi) await api('PUT', '/admin/ai', { provider: 'none' });
  fakeAi?.close();
});

test('the suite switch sits in the same place in Docket and Folio', async () => {
  const switcher = admin.getByRole('button', { name: /^Switch app/ });
  await admin.goto('/');
  await expect(switcher).toBeVisible();
  const docket = await switcher.boundingBox();
  await admin.goto('/folio');
  await expect(switcher).toBeVisible();
  const folio = await switcher.boundingBox();
  expect(docket && folio).toBeTruthy();
  for (const k of ['x', 'y', 'width', 'height'] as const) {
    expect(Math.abs(docket![k] - folio![k])).toBeLessThanOrEqual(1);
  }
});

test('the sidebar opens a space on its portada', async () => {
  await admin.goto('/folio');
  await admin
    .getByRole('navigation', { name: 'Spaces' })
    .getByRole('link', { name: SPACE.name })
    .click();
  await expect(admin).toHaveURL(new RegExp(`/folio/s/${SPACE.key}$`));
  await expect(admin.getByRole('heading', { level: 1, name: SPACE.name })).toBeVisible();
  await expect(admin.getByRole('searchbox', { name: `Search in ${SPACE.name}` })).toBeVisible();
  const sections = admin.getByRole('navigation', { name: `Sections of ${SPACE.name}` });
  await expect(sections.getByRole('link', { name: 'Specs 2' })).toBeVisible();
  await expect(sections.getByRole('link', { name: 'Architecture decisions 2' })).toBeVisible();
});

test('Specs filter by project, then by its features', async () => {
  await admin.goto(`/folio/s/${SPACE.key}/specs`);
  const rows = admin.getByRole('table').getByRole('row');
  await expect(rows).toHaveCount(3); // header + 2 specs
  await admin.getByRole('button', { name: 'Project: All' }).click();
  await admin.getByRole('menuitemradio', { name: /^NV/ }).click();
  await admin.getByRole('button', { name: /^Feature/ }).click();
  await admin.getByRole('menuitemcheckbox', { name: /^Pagos/ }).click();
  await admin.keyboard.press('Escape');
  await expect(rows).toHaveCount(2);
  await expect(admin.getByRole('link', { name: 'Etapa 1: pagos' })).toBeVisible();
  await admin.getByRole('button', { name: 'Remove Pagos' }).click();
  await expect(rows).toHaveCount(3);
});

test('Architecture decisions show the current ones by default', async () => {
  await admin.goto(`/folio/s/${SPACE.key}/decisions`);
  await expect(admin.getByRole('button', { name: 'Status: Current' })).toBeVisible();
  await expect(admin.getByText('1 replaced decision hidden')).toBeVisible();
  await expect(admin.getByRole('link', { name: 'Búsqueda híbrida con pgvector' })).toBeVisible();
  await expect(admin.getByRole('link', { name: 'Búsqueda solo de texto' })).toHaveCount(0);
});

test('a guide opens with its path back and the next page of its folder', async () => {
  await admin.goto(`/folio/s/${SPACE.key}/guides`);
  await admin
    .getByRole('link', { name: /Levanta la tienda en local/ })
    .first()
    .click();
  const path = admin.getByRole('navigation', { name: 'Path' });
  await expect(path.getByRole('link', { name: SPACE.name })).toBeVisible();
  await expect(path.getByRole('link', { name: 'Guides' })).toHaveAttribute(
    'href',
    `/folio/s/${SPACE.key}/guides`,
  );
  const more = admin.getByRole('navigation', { name: 'More in this folder' });
  await more.getByRole('link', { name: /Next Tu primer cambio/ }).click();
  await expect(admin.getByRole('heading', { level: 1, name: 'Tu primer cambio' })).toBeVisible();
  await expect(more.getByRole('link', { name: /Previous Levanta la tienda/ })).toBeVisible();
});

test('Manage opens the admin mode of the space', async () => {
  await admin.goto(`/folio/s/${SPACE.key}`);
  await admin.getByRole('link', { name: 'Manage' }).click();
  await expect(admin).toHaveURL(new RegExp(`/folio/s/${SPACE.key}/admin$`));
  await expect(admin.getByRole('tab', { name: 'Pages', selected: true })).toBeVisible();
  await admin.getByRole('tab', { name: 'Sections' }).click();
  await expect(admin.getByRole('tab', { name: 'Sections', selected: true })).toBeVisible();
  await admin.getByRole('tab', { name: 'Permissions' }).click();
  await expect(admin.getByRole('tab', { name: 'Permissions', selected: true })).toBeVisible();
});

test('Radi answers in Folio with the tools he used', async () => {
  test.skip(!FAKE_AI, 'Set RADICLE_E2E_FAKE_AI_URL so Radicle can reach the fake model.');
  fakeAi = await startFakeAi(FAKE_AI_PORT);
  await api('PUT', '/admin/ai', {
    provider: 'openai_compatible',
    base_url: FAKE_AI,
    chat_model: 'fake-docs-1',
  });
  await admin.goto(`/folio/s/${SPACE.key}`);
  await admin.getByRole('button', { name: 'Ask Radi for help' }).click();
  const chat = admin.getByRole('complementary', { name: 'Ask the docs' });
  const ask = chat.getByLabel('Your question');
  await ask.fill('¿Cómo levanto la tienda en local con docker?');
  await ask.press('Enter');
  await expect(chat.getByText('[1]').first()).toBeVisible({ timeout: 20_000 });
  await expect(chat.getByLabel('What Radi did').first()).toContainText('search_docs');
});
