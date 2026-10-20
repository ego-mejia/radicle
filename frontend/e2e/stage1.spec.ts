import { expect, test, type Page } from '@playwright/test';

/**
 * Stage 1 journey on a fresh instance. Steps share state, so they run in order.
 */
test.describe.configure({ mode: 'serial' });

const ADMIN = {
  name: 'Fernando',
  handle: 'fernando',
  email: 'fernando@example.com',
  password: 'e2e-password-1',
};
let page: Page;

test.beforeAll(async ({ browser }) => {
  page = await browser.newPage();
});

test.afterAll(async () => {
  await page.close();
});

async function createTicket(type: 'Task' | 'Bug' | 'Draft', title: string, area?: string) {
  await page.getByRole('button', { name: 'Create ticket' }).click();
  const dialog = page.getByRole('dialog', { name: 'Create ticket' });
  await dialog.getByRole('radio', { name: type }).click();
  await dialog.getByLabel('Title').fill(title);
  if (area) await dialog.getByLabel('Area *', { exact: true }).selectOption(area);
  await dialog.getByRole('button', { name: 'Create', exact: true }).click();
  await expect(dialog).toBeHidden();
}

async function openTicket(key: string) {
  await page.getByLabel('Search', { exact: true }).fill(key);
  await page.getByLabel('Search', { exact: true }).press('Enter');
  await expect(page.getByText(key, { exact: true }).first()).toBeVisible();
}

test('setup creates the first admin', async () => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/setup$/);
  await page.getByLabel('Name').fill(ADMIN.name);
  await page.getByLabel('Handle').fill(ADMIN.handle);
  await page.getByLabel('Email').fill(ADMIN.email);
  await page.getByLabel('Password').fill(ADMIN.password);
  await page.getByRole('button', { name: 'Create admin' }).click();
  await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible();
});

test('login after signing out', async () => {
  await page.getByRole('button', { name: 'Profile' }).click();
  await page.getByRole('menuitem', { name: 'Sign out' }).click();
  await expect(page).toHaveURL(/\/login/);
  await page.getByLabel('Email').fill(ADMIN.email);
  await page.getByLabel('Password').fill('wrong-password');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('alert')).toHaveText('Invalid email or password.');
  await page.getByLabel('Password').fill(ADMIN.password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible();
});

test('create project PA with four areas and milestone V1', async () => {
  await page.getByRole('button', { name: 'Create project' }).first().click();
  const dialog = page.getByRole('dialog', { name: 'Create project' });
  await dialog.getByLabel('Name').fill('ProyectoA');
  await dialog.getByLabel('Key').fill('PA');
  await dialog.getByRole('button', { name: 'Create' }).click();
  await expect(page).toHaveURL(/\/p\/PA\/settings\?tab=areas/);
  for (const area of ['Legal', 'Marketing', 'Backend', 'Frontend']) {
    await page.getByLabel('New area').fill(area);
    await page.getByRole('button', { name: 'Add' }).click();
    await expect(page.getByLabel('Area name').last()).toHaveValue(area);
  }
  await page.getByRole('tab', { name: 'Milestones' }).click();
  await page.getByRole('button', { name: 'New milestone' }).click();
  const milestone = page.getByRole('dialog', { name: 'New milestone' });
  await milestone.getByLabel('Name').fill('V1');
  await milestone.getByLabel('Target date').fill('2026-12-15');
  await milestone.getByRole('button', { name: 'Save' }).click();
  await expect(page.getByRole('heading', { name: 'V1' })).toBeVisible();
});

test('create a task, a bug and a draft: PA-1, PA-2, PA-3', async () => {
  await page.getByRole('link', { name: 'Board', exact: true }).click();
  await createTicket('Task', 'API de pagos', 'Backend');
  await createTicket('Bug', 'Checkout se congela', 'Frontend');
  await createTicket('Draft', 'Idea: pagar con QR');
  const todo = page.getByTestId('column-todo');
  await expect(todo.getByLabel('PA-1 API de pagos')).toBeVisible();
  await expect(todo.getByLabel('PA-2 Checkout se congela')).toBeVisible();
  await expect(todo.getByLabel('PA-3 Idea: pagar con QR')).toBeVisible();
});

test('drag a card to In Progress following the workflow', async () => {
  const card = page.getByTestId('column-todo').getByLabel('PA-1 API de pagos');
  const target = page.getByRole('region', { name: 'In Progress', exact: true });
  const from = (await card.boundingBox())!;
  const to = (await target.boundingBox())!;
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2);
  await page.mouse.down();
  await page.mouse.move(from.x + from.width / 2 + 20, from.y + from.height / 2, { steps: 5 });
  await page.waitForTimeout(400); // transitions load on drag start
  await page.mouse.move(to.x + to.width / 2, to.y + 80, { steps: 15 });
  await page.mouse.up();
  await expect(target.getByLabel('PA-1 API de pagos')).toBeVisible();
});

test('comment with a mention', async () => {
  await openTicket('PA-1');
  const editor = page.getByLabel('Write a comment. Markdown and @mentions work.');
  await editor.click();
  await page.keyboard.type('Revisando con @fernando');
  await page.getByRole('button', { name: 'Comment', exact: true }).click();
  await expect(page.locator('.mention', { hasText: '@fernando' })).toBeVisible();
});

test('link PA-2 as blocked by PA-1 and see the warning', async () => {
  await openTicket('PA-1');
  await page.getByRole('button', { name: 'Add link' }).click();
  await page.getByLabel('Ticket key, e.g. PA-4').fill('PA-2');
  await page.getByRole('button', { name: 'Add', exact: true }).click();
  await expect(page.getByText('PA-2', { exact: true }).last()).toBeVisible();
  await openTicket('PA-2');
  await expect(page.getByText('is blocked by')).toBeVisible();
  await page.getByRole('button', { name: 'Status' }).click();
  await page.getByRole('menuitem', { name: /In Progress/ }).click();
  await expect(page.getByText('Moved while blocked by PA-1.')).toBeVisible();
});

test('search with RQL and see errors in place', async () => {
  await page.goto('/p/PA/list');
  const bar = page.getByLabel('RQL query');
  await bar.fill('prioridad = high');
  await bar.press('Enter');
  await expect(page.getByRole('alert')).toContainText("Did you mean 'priority'");
  await bar.fill('project = PA AND type = bug');
  await bar.press('Enter');
  await expect(page.getByRole('row')).toHaveCount(2);
  await expect(page.getByRole('cell', { name: 'Checkout se congela' })).toBeVisible();
});

test('turn the draft into a task', async () => {
  await openTicket('PA-3');
  await page.getByRole('button', { name: 'More' }).first().click();
  await page.getByRole('menuitem', { name: 'Change type' }).click();
  const dialog = page.getByRole('dialog', { name: 'Change type of PA-3' });
  await dialog.getByLabel('Type').selectOption('task');
  await dialog.getByLabel('Area').selectOption('Legal');
  await dialog.getByRole('button', { name: 'Change type' }).click();
  await expect(page.getByRole('button', { name: 'Status' })).toContainText('To Do');
  await page.getByRole('tab', { name: 'History' }).click();
  await expect(page.getByText('changed the type')).toBeVisible();
});

test('create an agent and copy its token', async () => {
  await page.goto('/admin?tab=agents');
  await page.getByRole('button', { name: 'New agent' }).click();
  const dialog = page.getByRole('dialog', { name: 'New agent' });
  await dialog.getByLabel('Name').fill('Backend agent');
  await dialog.getByLabel('Handle').fill('agent-backend');
  await dialog.getByRole('button', { name: 'Create' }).click();
  await expect(page.getByText('Copy this token now. It will not be shown again.')).toBeVisible();
  const token = await page.getByTestId('copy-Token').textContent();
  expect(token).toMatch(/^rdc_[A-Za-z0-9]{40}$/);
  await page.getByRole('button', { name: 'Copy Token' }).click();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(token);
  await expect(page.getByTestId('copy-Claude Code')).toContainText(
    'claude mcp add --transport http radicle',
  );
});
