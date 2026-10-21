import type { Server } from 'node:http';
import { expect, test, type Page } from '@playwright/test';
// @ts-expect-error a plain .mjs helper, also runnable on its own with node
import { startFakeAi } from './fixtures/fake-ai.mjs';

/**
 * Folio phase 4: a build spec makes its Docket tickets and shows their progress, Docket
 * shows the docs of a ticket, and the docs chat answers with a citation that opens the
 * section. Runs after suite.spec.ts on the same instance (it signs in as its admin).
 *
 * The chat runs against a deterministic OpenAI-compatible server (fixtures/fake-ai.mjs)
 * that Radicle reaches at RADICLE_E2E_FAKE_AI_URL, by default the host as Docker sees it.
 * Where the app can't reach the host (e.g. CI on Linux without host-gateway), leave the
 * variable empty to skip the chat test.
 */
test.describe.configure({ mode: 'serial' });

const ADMIN = { email: 'fernando@example.com', password: 'e2e-password-1' };
const FAKE_AI_PORT = 8790;
const FAKE_AI =
  process.env.RADICLE_E2E_FAKE_AI_URL ??
  (process.env.CI ? '' : `http://host.docker.internal:${FAKE_AI_PORT}/v1`);
const META = {
  doc_type: 'how-to',
  labels: ['soporte'],
  owner: '@fernando',
  audiences: ['everyone'],
  language: 'es',
};
const SPEC = `## Objetivo y alcance

La primera versión de la tienda.

## Entregables

| # | Entregable | Incluye | Se acepta cuando |
| --- | --- | --- | --- |
| 1 | Catálogo | Listado y filtros | Veo los productos con su precio |
| 2 | Carrito | Agregar y quitar | El carrito sobrevive al recargar |

## Avance

::progress{}
`;
const GUIDE = `El agente de soporte contesta a los clientes. Avance en :ticket[AC-1].

# Conectar el agente de soporte

Crea el agente de soporte en Admin, Agentes, y conéctalo con su token desde Claude Code.
`;

let admin: Page;
let fakeAi: Server | undefined;
const ids: Record<string, string> = {};

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

async function page(title: string, md: string, meta: Record<string, unknown>) {
  const node = await api<{ id: string }>('POST', '/folio/nodes', {
    space: 'tienda',
    kind: 'page',
    title,
  });
  await api('PUT', `/folio/nodes/${node.id}/draft`, { content_md: md, metadata: meta });
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

  // Tolerates a second run against the same instance.
  await api('POST', '/projects', { key: 'AC', name: 'Acme Shop' }, true);
  await api('POST', '/projects/AC/areas', { name: 'Backend' }, true);
  await api('POST', '/projects/AC/milestones', { name: 'V1' }, true);
  await api('POST', '/projects/AC/tickets', {
    type: 'task',
    title: 'Conectar el agente de soporte',
    area: 'Backend',
  });
  await api('POST', '/folio/spaces', { key: 'tienda', name: 'Tienda' }, true);
  ids.spec = await page('Build spec de la tienda', SPEC, {
    ...META,
    doc_type: 'build-spec',
    description: 'Alcance, entregables y criterios de la primera versión de la tienda.',
  });
  ids.guide = await page('Agente de soporte', GUIDE, {
    ...META,
    description: 'Qué hace el agente de soporte de la tienda y cómo conectarlo.',
  });
  if (FAKE_AI) {
    fakeAi = await startFakeAi(FAKE_AI_PORT);
    await api('PUT', '/admin/ai', {
      provider: 'openai_compatible',
      base_url: FAKE_AI,
      chat_model: 'fake-docs-1',
    });
  }
});

test.afterAll(async () => {
  if (FAKE_AI) await api('PUT', '/admin/ai', { provider: 'none' });
  fakeAi?.close();
});

test('a build spec makes one ticket per deliverable and shows their progress', async () => {
  await admin.goto(`/folio/p/${ids.spec}`);
  await admin.getByRole('button', { name: 'Create tickets' }).click();
  const wizard = admin.getByRole('dialog');
  await expect(wizard.getByText('Catálogo')).toBeVisible();
  await wizard.getByLabel('Area').selectOption({ label: 'Backend' });
  await wizard.getByLabel('Milestone').selectOption({ label: 'V1' });
  await wizard.getByRole('button', { name: 'Create 2 tickets' }).click();
  await expect(wizard).toBeHidden();

  await admin.reload();
  const progress = admin.getByText('Ticket progress').locator('..').locator('..');
  const keys = progress.getByRole('link', { name: /^AC-\d+$/ });
  await expect(keys).toHaveCount(2);
  await expect(progress.getByText('0 of 2 done')).toBeVisible();

  // Back from Docket: the ticket carries its criterion and links to its deliverable.
  await keys.first().click();
  await expect(admin).toHaveURL(/\/t\/AC-\d+$/);
  await expect(admin.getByText('Veo los productos con su precio')).toBeVisible();
  await expect(
    admin.getByRole('link', { name: 'Build spec de la tienda', exact: true }),
  ).toBeVisible();
  await expect(admin.getByText(/deliverable/)).toBeVisible();

  // Running it again creates nothing new.
  const again = await api<{ items: unknown[] }>(
    'POST',
    `/folio/nodes/${ids.spec}/build-spec/tickets`,
    { project: 'AC', area: 'Backend' },
  );
  expect(again.items).toEqual([]);
});

test("a ticket's Docs panel lists the doc that mentions it", async () => {
  await admin.goto(`/folio/p/${ids.guide}`);
  await expect(admin.getByText('AC-1').first()).toBeVisible();
  await admin.goto('/t/AC-1');
  await expect(
    admin.getByRole('link', { name: 'Agente de soporte', exact: true }).first(),
  ).toBeVisible();
  await expect(admin.getByText(/mentions it/).first()).toBeVisible();
});

test('the chat answers with a citation that opens the section', async () => {
  test.skip(!FAKE_AI, 'Set RADICLE_E2E_FAKE_AI_URL so Radicle can reach the fake model.');
  await admin.goto('/folio');
  await admin.getByRole('button', { name: 'Ask', exact: true }).first().click();
  const chat = admin.getByRole('complementary', { name: 'Ask the docs' });
  const ask = chat.getByLabel('Your question');
  await ask.fill('¿Cómo conecto el agente de soporte?');
  await ask.press('Enter');
  // The answer cites [1]; its source opens the doc at the cited section.
  await expect(chat.getByText('[1]').first()).toBeVisible({ timeout: 20_000 });
  const source = chat.getByRole('link', { name: /conecta/i }).first();
  await source.click();
  await expect(admin).toHaveURL(/\/folio\/p\/[^#]+#[a-z-]*conecta/);

  await ask.fill('¿Cuál es la política de vacaciones?');
  // The answer is saved when its stream ends; leaving earlier would drop it.
  const answered = admin.waitForEvent('requestfinished', (r) => r.url().endsWith('/messages'));
  await ask.press('Enter');
  await expect(chat.getByText(/no cubren esto/)).toBeVisible({ timeout: 20_000 });
  await answered;

  // Both answers were saved: the one without a source waits in Admin, Chat.
  await admin.goto('/folio/admin');
  await admin.getByRole('tab', { name: 'Chat' }).click();
  await expect(admin.getByText('¿Cuál es la política de vacaciones?').first()).toBeVisible();
});
