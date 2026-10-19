import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';

/**
 * Stage 2 journey. Runs after stage1.spec.ts on the same instance (PA with four areas,
 * V1, PA-1..PA-3 and the admin), with the worker running.
 */
test.describe.configure({ mode: 'serial' });

const ADMIN = { email: 'fernando@example.com', password: 'e2e-password-1' };
let page: Page;

test.beforeAll(async ({ browser }) => {
  page = await browser.newPage();
  await page.goto('/login');
  await page.getByLabel('Email').fill(ADMIN.email);
  await page.getByLabel('Password').fill(ADMIN.password);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Projects' })).toBeVisible();
});

test.afterAll(async () => {
  await page.close();
});

async function settings(project: string, tab: string) {
  await page.goto(`/p/${project}/settings?tab=${tab}`);
}

async function createTicket(fill: (dialog: ReturnType<Page['getByRole']>) => Promise<void>) {
  await page.getByRole('button', { name: 'Create ticket' }).click();
  const dialog = page.getByRole('dialog', { name: 'Create ticket' });
  await fill(dialog);
  await dialog.getByRole('button', { name: 'Create', exact: true }).click();
  return dialog;
}

test('detach PA and give bugs a required Environment field', async () => {
  await settings('PA', 'general');
  await page.getByRole('button', { name: 'Detach' }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Detach' }).click();
  await expect(page.getByText('Independent project, created from')).toBeVisible();

  await settings('PA', 'fields');
  await page.getByRole('button', { name: 'New field' }).click();
  const field = page.getByRole('dialog', { name: 'New field' });
  await field.getByLabel('Name').fill('Environment');
  await field.getByLabel('Type', { exact: true }).selectOption('select');
  await field.getByLabel('Value').first().fill('prod');
  await field.getByRole('button', { name: 'Add option' }).click();
  await field.getByLabel('Value').last().fill('dev');
  await field.getByRole('checkbox', { name: 'Task' }).uncheck();
  await field.getByRole('checkbox', { name: 'Draft' }).uncheck();
  await field.getByRole('button', { name: 'Create' }).click();
  await expect(page.getByText('cf.environment')).toBeVisible();

  await settings('PA', 'screens');
  await page.getByRole('tab', { name: 'Bug' }).click();
  const create = page.getByRole('region', { name: 'Create' });
  await create.getByRole('checkbox', { name: 'Custom screen' }).check();
  await create.getByRole('checkbox', { name: 'Show Environment' }).check();
  await create.getByRole('checkbox', { name: 'Environment required' }).check();
  await create.getByRole('checkbox', { name: 'Show Area' }).check();
  await create.getByRole('checkbox', { name: 'Area required' }).check();
  await page.getByRole('button', { name: 'Save' }).click();

  await page.goto('/p/PA/board');
  const dialog = await createTicket(async (d) => {
    await d.getByRole('radio', { name: 'Bug' }).click();
    await d.getByLabel('Title *').fill('Pago duplicado');
  });
  await expect(dialog.getByText('Required').first()).toBeVisible();
  await dialog.getByLabel('Area', { exact: false }).first().selectOption('Backend');
  await dialog.getByLabel('Environment *').selectOption('prod');
  await dialog.getByRole('button', { name: 'Create', exact: true }).click();
  await expect(dialog).toBeHidden();
});

test('checklist_complete stops Complete and lists what is open', async () => {
  await settings('PA', 'workflows');
  await page.getByRole('button', { name: 'Complete' }).first().click();
  const transition = page.getByRole('dialog');
  await transition.getByLabel('Add to Validators').selectOption('checklist_complete');
  await transition.getByRole('button', { name: 'Save' }).click();
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page.getByText('Saved')).toBeVisible();

  await createTicket(async (d) => {
    await d.getByLabel('Title *').fill('Lanzar campaña');
    await d.getByLabel('Area *').selectOption('Marketing');
  });
  await page.goto('/p/PA/list?q=' + encodeURIComponent('title ~ "Lanzar campaña"'));
  await page.getByRole('cell', { name: 'Lanzar campaña' }).click();
  const panel = page.getByRole('dialog');
  await panel
    .getByRole('button', { name: 'Edit description' })
    .or(panel.getByText('Add a description'))
    .first()
    .click();
  await page.keyboard.type('- [ ] Copy');
  await panel.getByRole('button', { name: 'Save' }).click();
  for (const status of ['In Progress', 'In Review']) {
    await panel.getByRole('button', { name: 'Status' }).click();
    await page.getByRole('menuitem', { name: new RegExp(status) }).click();
  }
  await panel.getByRole('button', { name: 'Status' }).click();
  await page.getByRole('menuitem', { name: /Done.*Complete/ }).click();
  await page.getByRole('radio', { name: 'Done' }).click();
  await page.getByRole('button', { name: 'Move to Done' }).click();
  await expect(page.getByText("1 checklist items are still open: 'Copy'.")).toBeVisible();
});

test('template from PA reaches PB but not the detached PC', async () => {
  await settings('PA', 'general');
  await page.getByRole('button', { name: 'Save as template' }).click();
  const save = page.getByRole('dialog', { name: 'Save as template' });
  await save.getByLabel('Name').fill('Producto digital');
  await save.getByRole('button', { name: 'Create' }).click();
  await expect(page.getByRole('heading', { name: 'Producto digital' })).toBeVisible();
  const templateUrl = page.url();

  for (const [key, mode] of [
    ['PB', 'Linked'],
    ['PC', 'Independent'],
  ] as const) {
    await page.goto('/');
    await page.getByRole('button', { name: 'Create project' }).first().click();
    const dialog = page.getByRole('dialog', { name: 'Create project' });
    await dialog.getByLabel('Name').fill(`Proyecto ${key}`);
    await dialog.getByLabel('Key').fill(key);
    await dialog
      .getByLabel('Template', { exact: true })
      .selectOption({ label: 'Producto digital' });
    await dialog.getByRole('radio', { name: new RegExp(mode) }).check();
    await dialog.getByRole('button', { name: 'Create' }).click();
    await expect(page).toHaveURL(new RegExp(`/p/${key}/settings`));
  }

  await page.goto(templateUrl.split('?')[0] + '?tab=workflows&type=task');
  await page.getByRole('button', { name: 'Add status' }).click();
  await page.getByLabel('Status name').last().fill('Blocked');
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page.getByText(/Saved as version 2/)).toBeVisible();
  await expect(page.getByText('Done', { exact: true }).first()).toBeVisible({ timeout: 20_000 });

  await settings('PB', 'workflows');
  await expect(page.getByText('Blocked').first()).toBeVisible({ timeout: 20_000 });
  await settings('PC', 'workflows');
  await expect(page.getByLabel('Status name').filter({ hasText: 'Blocked' })).toHaveCount(0);
});

test('attach a screenshot, shrink it, log time and vote', async () => {
  await page.goto('/t/PA-1');
  const png = readFileSync(new URL('./fixtures/screenshot.png', import.meta.url));
  await page.locator('input[type="file"]').setInputFiles({
    name: 'screenshot.png',
    mimeType: 'image/png',
    buffer: png,
  });
  await page
    .getByRole('dialog', { name: 'Image size' })
    .getByRole('button', { name: 'Upload' })
    .click();
  const tile = page.getByRole('button', { name: 'Open screenshot.png' });
  await expect(tile).toBeVisible();
  await page.getByRole('button', { name: 'Actions for screenshot.png' }).click();
  await page.getByRole('menuitem', { name: /Medium/ }).click();
  await expect(page.getByText(/screenshot.png is now/)).toBeVisible();

  await page.getByRole('button', { name: 'Log time' }).click();
  const log = page.getByRole('dialog', { name: 'Log time on PA-1' });
  await log.getByLabel('Time').fill('1h 30m');
  await log.getByRole('button', { name: 'Log time' }).click();
  await expect(page.getByText('Spent: 1h 30m')).toBeVisible();

  await page.getByRole('button', { name: /Vote \(0\)/ }).click();
  await expect(page.getByRole('button', { name: /Remove my vote \(1\)/ })).toBeVisible();
});

test('clone PA-1, then move the clone to PB and follow the old link', async () => {
  await page.goto('/t/PA-1');
  await page.getByRole('button', { name: 'More' }).first().click();
  await page.getByRole('menuitem', { name: 'Clone' }).click();
  await page
    .getByRole('dialog', { name: 'Clone PA-1' })
    .getByRole('button', { name: 'Clone' })
    .click();
  await expect(page).toHaveURL(/\/t\/PA-(?!1$)\d+$/);
  const cloneKey = page.url().split('/t/')[1]!;

  await page.getByRole('button', { name: 'More' }).first().click();
  await page.getByRole('menuitem', { name: 'Move to project' }).click();
  const move = page.getByRole('dialog', { name: `Move ${cloneKey}` });
  await move.getByLabel('To project').selectOption('PB');
  await move.getByRole('button', { name: 'Move' }).click();
  await expect(page).toHaveURL(/\/t\/PB-\d+$/);
  const newKey = page.url().split('/t/')[1]!;

  await page.goto(`/t/${cloneKey}`);
  await expect(page).toHaveURL(new RegExp(`/t/${newKey}$`));
});

test('bulk-tag two tickets with a preview, then save the filter', async () => {
  await page.goto('/p/PA/list?q=' + encodeURIComponent('project = PA ORDER BY key ASC'));
  await page.getByRole('checkbox', { name: 'Select PA-1' }).check();
  await page.getByRole('checkbox', { name: 'Select PA-2' }).check();
  await page.getByRole('button', { name: 'Tags', exact: true }).click();
  const bulk = page.getByRole('dialog');
  await bulk.getByLabel('Action').selectOption('add_tag');
  await bulk.getByLabel('Tag').fill('e2e');
  await bulk.getByRole('button', { name: 'Preview' }).click();
  await expect(bulk.getByText('2 would change, 0 would fail:')).toBeVisible();
  await bulk.getByRole('button', { name: 'Apply to 2 tickets' }).click();
  await expect(bulk.getByText('2 changed, 0 failed.')).toBeVisible();
  await bulk.getByRole('button', { name: 'Close' }).first().click();

  await page.getByRole('button', { name: 'Save', exact: true }).first().click();
  const save = page.getByRole('dialog', { name: 'Save current filter' });
  await save.getByLabel('Name').fill('Con e2e');
  await save.getByRole('button', { name: 'Save' }).click();
  await expect(page.getByRole('button', { name: 'Con e2e', exact: true })).toBeVisible();
});

test('daily work with the keyboard only', async () => {
  await page.goto('/');
  await page.keyboard.press('g');
  await page.keyboard.press('m');
  await expect(page).toHaveURL(/\/me\/tickets/);
  await page.keyboard.press('Control+k');
  await page.keyboard.type('PA-2');
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/\/t\/PA-2$/);
  await expect(page.getByLabel('Assignee')).toBeEnabled();
  await page.keyboard.press('a');
  await expect(page.getByLabel('Assignee')).toHaveValue('fernando');
  await page.keyboard.press('m');
  await expect(page.getByRole('menuitem').first()).toBeVisible();
  await page.keyboard.press('Escape');
  await page.keyboard.press('?');
  await expect(page.getByRole('dialog', { name: 'Keyboard shortcuts' })).toBeVisible();
  await page.keyboard.press('Escape');
  await page.keyboard.press('c');
  await expect(page.getByRole('dialog', { name: 'Create ticket' })).toBeVisible();
  await page.keyboard.press('Escape');
});
