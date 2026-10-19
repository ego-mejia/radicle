import { fileURLToPath } from 'node:url';
import { expect, test, type Browser, type Page } from '@playwright/test';

/**
 * Stage 4 journey: the public form feeds the inbox, the matrix of permissions and
 * restricted tickets. Runs after the earlier specs on the same instance (PA with the
 * Backend area and the admin).
 */
test.describe.configure({ mode: 'serial' });

const ADMIN = { email: 'fernando@example.com', password: 'e2e-password-1' };
const MEMBER = { handle: 'renata', email: 'renata@example.com', password: 'e2e-password-2' };
const SCREENSHOT = fileURLToPath(new URL('./fixtures/screenshot.png', import.meta.url));
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

/** Calls the API with the page's session (cookie + CSRF), like the UI does. */
async function api<T = unknown>(
  method: string,
  url: string,
  body?: unknown,
  ok: number[] = [],
  headers: Record<string, string> = {},
): Promise<T> {
  return page.evaluate(
    async ({ method, url, body, ok, headers }) => {
      const csrf = document.cookie.match(/radicle_csrf=([^;]+)/)?.[1] ?? '';
      const r = await fetch(`/api/v1${url}`, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf, ...headers },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const text = await r.text();
      if (!r.ok && !ok.includes(r.status)) throw new Error(`${method} ${url}: ${r.status} ${text}`);
      return text && r.ok ? JSON.parse(text) : null;
    },
    { method, url, body, ok, headers },
  );
}

test.beforeAll(async ({ browser }) => {
  page = await signIn(browser, ADMIN);
  await api('PUT', '/projects/PA/inbox-settings', { enabled: true, public_slug: 'pa' });
  await api(
    'POST',
    '/users',
    {
      handle: MEMBER.handle,
      display_name: 'Renata',
      email: MEMBER.email,
      password: MEMBER.password,
    },
    [409],
  );
  await api('PUT', `/projects/PA/members/${MEMBER.handle}`, { role: 'member' });
});

test.afterAll(async () => {
  await api('DELETE', '/projects/PA/permissions');
  await page.close();
});

test('a complaint from the public form goes through the inbox and back to the sender', async ({
  browser,
}) => {
  // Someone without an account, in a separate browser context.
  const outsider = await (await browser.newContext()).newPage();
  await outsider.goto('/b/pa');
  await outsider.getByLabel('Complaint').check();
  const title = `Export to PDF cuts the last page ${Date.now()}`;
  await outsider.getByLabel('Title').fill(title);
  await outsider.getByLabel('Tell us more').fill('Every report loses its last page when exported.');
  await outsider.getByLabel('Your email (optional)').fill('client@example.org');
  await outsider.getByLabel(/Screenshots/).setInputFiles(SCREENSHOT);
  await expect(outsider.getByText('Ready to send.')).toBeVisible({ timeout: 30_000 });
  await outsider.waitForTimeout(3_000); // the form refuses anything sent faster than a human
  await outsider.getByRole('button', { name: 'Send' }).click();
  const code = (await outsider.getByTestId('tracking-code').textContent())?.trim() ?? '';
  expect(code).toMatch(/^[0-9A-Z]{10}$/);

  // The team sees it in the inbox as coming from a user, scores it and approves it.
  await page.goto('/p/PA/inbox');
  const row = page.getByRole('row').filter({ hasText: title });
  await expect(row.getByText('User', { exact: true })).toBeVisible();
  await expect(row.getByText('Complaint', { exact: true })).toBeVisible();
  const key = ((await row.getAttribute('data-testid')) ?? '').replace('inbox-', '');
  expect(key).toMatch(/^PA-\d+$/);
  await row.getByLabel(`Impact of ${key}`).selectOption('5');
  await row.getByLabel(`Effort of ${key}`).selectOption('1');
  await page.getByRole('button', { name: 'Matrix' }).click();
  const dot = page.getByRole('group', { name: 'Matrix' }).getByTestId(`dot-${key}`);
  await expect(dot).toBeVisible();
  await page.getByRole('button', { name: 'Table' }).click();
  await page.getByRole('button', { name: `Actions for ${key}` }).click();
  await page.getByRole('menuitem', { name: 'Approve and convert' }).click();
  const dialog = page.getByRole('dialog', { name: `Approve ${key}` });
  await dialog.getByLabel('Convert to').selectOption('bug');
  await dialog.getByLabel('Area *').selectOption('Backend');
  await dialog.getByRole('button', { name: 'Approve and convert' }).click();
  await expect(page.getByText(`${key} is now a bug.`)).toBeVisible();
  const ticket = await api<{ type: string; area: string; origin: string }>(
    'GET',
    `/tickets/${key}`,
  );
  expect([ticket.type, ticket.area, ticket.origin]).toEqual(['bug', 'Backend', 'user']);

  // The sender follows it with the code.
  await outsider.goto(`/b/pa/t/${code}`);
  await expect(outsider.getByTestId('state')).toHaveText('Accepted');
  await outsider.close();
});

test('turning a permission off hides the button for that role', async ({ browser }) => {
  const { key } = await api<{ key: string }>('POST', '/projects/PA/tickets', {
    type: 'task',
    area: 'Backend',
    title: 'Ticket for the comment permission',
  });
  const member = await signIn(browser, MEMBER);
  await member.goto(`/t/${key}`);
  await expect(member.getByRole('button', { name: 'Comment', exact: true })).toBeVisible();

  await page.goto('/p/PA/settings?tab=permissions');
  const box = page.getByLabel('comment.create member');
  await box.click(); // saved on click; it unticks once the server confirms
  await expect(box).not.toBeChecked();

  await member.reload();
  await expect(
    member.getByRole('heading', { name: 'Ticket for the comment permission' }),
  ).toBeVisible();
  await expect(member.getByRole('button', { name: 'Comment', exact: true })).toHaveCount(0);
  await member.close();
});

test('a restricted ticket is invisible to a member outside its level', async ({ browser }) => {
  const level = await api<{ id: string; name: string }>('POST', '/projects/PA/security-levels', {
    name: `Legal ${Date.now()}`,
  });
  const { key } = await api<{ key: string }>('POST', '/projects/PA/tickets', {
    type: 'task',
    area: 'Backend',
    title: 'Contract with the new supplier',
  });
  await api('PATCH', `/tickets/${key}`, { security_level: level.name }, [], { 'If-Match': '1' });
  await page.goto(`/t/${key}`);
  await expect(
    page.getByText(`Restricted: only "${level.name}" can see this ticket.`),
  ).toBeVisible();

  const member = await signIn(browser, MEMBER);
  await member.goto(`/t/${key}`);
  await expect(member.getByText('This ticket does not exist or you cannot see it.')).toBeVisible();
  const found = await member.evaluate(async (title) => {
    const q = encodeURIComponent(`text ~ "${title}"`);
    const r = await fetch(`/api/v1/tickets?q=${q}`);
    return (await r.json()).items.length as number;
  }, 'Contract with the new supplier');
  expect(found).toBe(0);
  // The admin still finds it.
  const mine = await api<{ items: unknown[] }>(
    'GET',
    `/tickets?q=${encodeURIComponent('text ~ "Contract with the new supplier"')}`,
  );
  expect(mine.items.length).toBeGreaterThan(0);
  await member.close();
});
