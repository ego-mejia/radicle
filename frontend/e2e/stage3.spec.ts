import { expect, test, type Page } from '@playwright/test';

/**
 * Stage 3 journey. Runs after stage1 and stage2 on the same instance (PA detached, with
 * tickets and the admin), with the worker running.
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

/** Calls the API with the page's session (cookie + CSRF), like the UI does. */
async function api<T = unknown>(method: string, path: string, body?: unknown): Promise<T> {
  return page.evaluate(
    async ({ method, path, body }) => {
      const csrf = document.cookie.match(/radicle_csrf=([^;]+)/)?.[1] ?? '';
      const r = await fetch(`/api/v1${path}`, {
        method,
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      const text = await r.text();
      if (!r.ok) throw new Error(`${method} ${path}: ${r.status} ${text}`);
      return text ? JSON.parse(text) : null;
    },
    { method, path, body },
  );
}

async function newTicket(fields: Record<string, unknown>): Promise<string> {
  const t = await api<{ key: string }>('POST', '/projects/PA/tickets', {
    type: 'task',
    area: 'Backend',
    ...fields,
  });
  return t.key;
}

async function moveTo(key: string, ...statuses: string[]) {
  for (const status of statuses) {
    await api('POST', `/tickets/${key}/transitions`, { to_status: status });
  }
}

test('a Review column with In Review and QA Verified turns red past WIP 3', async () => {
  await page.goto('/p/PA/board');
  await page.getByRole('button', { name: 'Configure' }).click();
  await expect(page.getByRole('heading', { name: 'Main' })).toBeVisible();
  // Main comes with In Review (In Review and QA Verified): turn it into Review, WIP 3.
  const column = page.getByRole('region', { name: 'Column 3' });
  await column.getByLabel('Column name').fill('Review');
  await column.getByLabel('WIP limit').fill('3');
  for (const name of [/In Review/, /QA Verified/]) {
    for (const box of await column.getByRole('checkbox', { name }).all()) await box.check();
  }
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page.getByText('Board saved')).toBeVisible();

  // Earlier specs may have left tickets in review: fill up to the limit, then one more.
  await page.goto('/p/PA/board');
  const review = page.getByRole('region', { name: 'Review' });
  await expect(review).toContainText('/ 3');
  const already = Number((await review.locator('h2 + span').innerText()).split('/')[0]);
  const keys: string[] = [];
  for (let i = 0; i < 4 - already; i++) {
    const kind = i % 2 ? 'bug' : 'task';
    const extra = kind === 'bug' ? { custom_fields: { environment: 'prod' } } : {};
    const key = await newTicket({ type: kind, title: `Revisar ${i}`, tags: ['e3'], ...extra });
    keys.push(key);
    await moveTo(key, 'In Progress', kind === 'task' ? 'In Review' : 'QA Verified');
    if (already + i + 1 === 3) {
      await page.reload();
      await expect(review).toContainText('3 / 3');
    }
  }
  await page.reload();
  await expect(review).toContainText('4 / 3');
  await expect(review.getByLabel(new RegExp(keys.at(-1)!))).toBeVisible();

  // Quick filter and swimlanes answer right away.
  await page.getByRole('button', { name: 'Only bugs' }).click();
  await expect(review).not.toContainText('Revisar 0');
  await page.getByLabel('Swimlanes').selectOption('area');
  await expect(page.getByRole('button', { name: /^Backend \d+ tickets?$/ })).toBeVisible();
});

test('run a whole sprint: plan, start, add mid-way and close to #backlog', async () => {
  const keys: string[] = [];
  for (const [title, hours] of [
    ['Checkout v2', 8],
    ['Recibos PDF', 5],
    ['Webhooks', 3],
  ] as const) {
    keys.push(await newTicket({ title, estimate_hours: hours, tags: ['backlog'] }));
  }
  await page.goto('/p/PA/backlog');
  await page.getByRole('button', { name: 'Create Scrum board' }).click();
  await page.getByRole('button', { name: 'New sprint' }).click();
  const sprint = page.getByRole('region', { name: 'Sprint 1' });
  await expect(sprint).toBeVisible();

  const backlog = page.getByRole('region', { name: 'Backlog' });
  for (const key of keys.slice(0, 2)) {
    await backlog.getByRole('checkbox', { name: `Select ${key}` }).check();
  }
  await page.getByLabel('Move to…').selectOption({ label: 'Sprint 1' });
  await page.getByRole('button', { name: 'Move', exact: true }).click();
  await expect(sprint.getByText(keys[0]!)).toBeVisible();
  await expect(sprint).toContainText('2 tickets · 13h');

  await sprint.getByRole('button', { name: 'Start sprint' }).click();
  const start = page.getByRole('dialog', { name: 'Start Sprint 1' });
  await start.getByLabel('Goal').fill('Cobrar en línea');
  await start.getByLabel('Capacity (hours)').fill('12');
  await start.getByRole('button', { name: 'Start sprint' }).click();
  await expect(start).toBeHidden();
  await expect(sprint.getByText('Active')).toBeVisible();
  await expect(sprint.getByRole('meter', { name: 'Capacity' })).toContainText('13h of 12h');

  // Mid-sprint addition: a scope change.
  await backlog.getByRole('checkbox', { name: `Select ${keys[2]}` }).check();
  await page.getByLabel('Move to…').selectOption({ label: 'Sprint 1' });
  await page.getByRole('button', { name: 'Move', exact: true }).click();
  await expect(sprint.getByText(keys[2]!)).toBeVisible();
  await moveTo(keys[0]!, 'In Progress', 'In Review');
  await api('POST', `/tickets/${keys[0]}/transitions`, { to_status: 'Done', resolution: 'done' });

  await page.reload();
  await sprint.getByRole('button', { name: 'Complete sprint' }).click();
  const close = page.getByRole('dialog', { name: 'Complete Sprint 1' });
  await expect(close.getByText('Added after start')).toBeVisible();
  await expect(close.locator('dd').nth(1)).toContainText('2');
  await close.getByRole('button', { name: 'Complete sprint' }).click();
  await expect(close).toBeHidden();
  await expect(backlog.getByText(keys[1]!)).toBeVisible();
  await expect(backlog.getByText(keys[2]!)).toBeVisible();
  const found = await api<{ items: { key: string }[] }>(
    'GET',
    `/tickets?q=${encodeURIComponent('#backlog AND title ~ "Recibos"')}`,
  );
  expect(found.items.map((t) => t.key)).toEqual([keys[1]]);
});

test('the sprint report and burndown add up, and V1 has a forecast', async () => {
  await page.goto('/p/PA/reports?type=sprint');
  const chart = page.getByTestId('report-sprint');
  await expect(chart.getByText('Added after start')).toBeVisible();
  await expect(chart).toContainText('13h'); // committed: 8 h + 5 h
  await page.getByRole('link', { name: 'Burndown' }).click();
  await expect(page.getByTestId('report-burndown')).toContainText('Committed');
  await expect(page.getByText(/Data \(\d+ rows?\)/)).toBeVisible();
  await page.getByRole('link', { name: 'Milestone progress' }).click();
  await expect(page.getByTestId('report-milestone_progress')).toContainText('Forecast');
  const csv = page.getByRole('link', { name: 'Export CSV' });
  await expect(csv).toHaveAttribute('href', /milestone_progress\.csv\?project=PA&milestone=V1/);
});

test('drag a bar on the timeline and see a dependency in red', async () => {
  const a = await newTicket({
    title: 'Diseño API',
    start_date: '2026-11-02',
    due_date: '2026-11-06',
    milestone: 'V1',
  });
  const b = await newTicket({
    title: 'Cliente API',
    start_date: '2026-11-09',
    due_date: '2026-11-13',
    milestone: 'V1',
  });
  await api('POST', `/tickets/${a}/links`, { type: 'blocks', target: b });

  await page.goto('/p/PA/timeline?zoom=week&q=' + encodeURIComponent('title ~ "API"'));
  await expect(page.getByTestId('milestone-V1')).toBeAttached();
  const dep = page.getByTestId(`dep-${a}-${b}`);
  await expect(dep).toHaveAttribute('data-conflict', 'false');

  // Week zoom is 36 px per day: drag 5 days right.
  const bar = page.getByTestId(`bar-${a}`).locator('rect').first();
  await bar.scrollIntoViewIfNeeded();
  const box = (await bar.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 90, box.y + box.height / 2, { steps: 5 });
  await page.mouse.move(box.x + box.width / 2 + 180, box.y + box.height / 2, { steps: 5 });
  await page.mouse.up();

  await expect(dep).toHaveAttribute('data-conflict', 'true');
  const ticket = await api<{ start_date: string; due_date: string }>('GET', `/tickets/${a}`);
  expect([ticket.start_date, ticket.due_date]).toEqual(['2026-11-07', '2026-11-11']);
  const history = await api<{ items: { field: string | null }[] }>('GET', `/tickets/${a}/history`);
  expect(history.items.some((e) => e.field === 'start_date')).toBe(true);
});

test('build "V1 Go to market" and share it with the project', async ({ browser }) => {
  await page.goto('/dashboards');
  await page.getByLabel('New dashboard name').fill('V1 Go to market');
  await page.getByRole('button', { name: 'Create dashboard' }).click();
  await expect(page.getByRole('heading', { name: 'V1 Go to market' })).toBeVisible();
  await page.getByRole('button', { name: 'Edit' }).click();

  async function add(widget: string, fill?: (d: ReturnType<Page['getByRole']>) => Promise<void>) {
    await page.getByRole('button', { name: 'Add widget' }).click();
    await page
      .getByRole('dialog', { name: 'Add widget' })
      .getByRole('button', { name: widget })
      .click();
    const dialog = page.getByRole('dialog', { name: new RegExp(`^${widget.split(' ')[0]}`) });
    if (fill) await fill(dialog);
    await dialog.getByRole('button', { name: 'Save' }).click();
    await expect(dialog).toBeHidden();
  }
  await add('Milestone progress', async (d) => {
    await d.getByLabel('Project').selectOption('PA');
    await d.getByLabel('Milestone').fill('V1');
  });
  await add('Distribution', async (d) => {
    await d.getByLabel('Title').fill('Open bugs by area');
    await d.getByLabel('RQL').fill('project = PA AND type = bug AND category != done');
    await d.getByLabel('Chart').selectOption('pie');
  });
  await add('Blocked tickets', async (d) => {
    await d.getByLabel('RQL').fill('project = PA');
  });
  await expect(page.getByTestId('widget-Milestone progress')).toContainText('%');
  await expect(page.getByTestId('widget-Blocked tickets')).toContainText('blocked by');
  await page.getByRole('button', { name: 'Done' }).click();

  await page.getByRole('button', { name: 'Share' }).click();
  const share = page.getByRole('dialog', { name: 'Share' });
  await share.getByLabel('Who sees it').selectOption('project');
  await share.getByLabel('Project').selectOption('PA');
  await share.getByRole('button', { name: 'Save' }).click();
  await expect(share).toBeHidden();
  const url = page.url();

  // Someone else in the project sees it, computed with their own permissions.
  await api('POST', '/users', {
    handle: 'ana',
    display_name: 'Ana',
    email: 'ana@example.com',
    password: 'ana-password-1',
  });
  await api('PUT', '/projects/PA/members/ana', { role: 'viewer' });
  const other = await browser.newPage();
  await other.goto('/login');
  await other.getByLabel('Email').fill('ana@example.com');
  await other.getByLabel('Password').fill('ana-password-1');
  await other.getByRole('button', { name: 'Sign in' }).click();
  await expect(other.getByRole('heading', { name: 'Projects' })).toBeVisible();
  await other.goto(url);
  await expect(other.getByRole('heading', { name: 'V1 Go to market' })).toBeVisible();
  await expect(other.getByTestId('widget-Open bugs by area')).toBeVisible();
  await expect(other.getByRole('button', { name: 'Edit' })).toHaveCount(0);
  await other.close();
});
