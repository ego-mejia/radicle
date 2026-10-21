import { expect, test } from '@playwright/test';
import {
  HEIGHT_MESSAGE,
  THEME_MESSAGE,
  VISUAL_SANDBOX,
  visualDocument,
} from '../src/features/folio/components/VisualFrame/visualDocument';

/**
 * The Visual block's sandbox in a real browser (Folio 3.3): a visual can't read the page
 * around it, its cookies or its storage, and it can't reach the network. Needs no Radicle:
 * the page is served by the test itself at http://radicle.test.
 *   pnpm exec playwright test e2e/visual-sandbox.spec.ts
 */
const ORIGIN = 'http://radicle.test';

// Everything a hostile visual would try; it reports each outcome to the page.
const PROBE = `<div style="height:420px">probe</div><script>
const report = (name, value) => parent.postMessage({ probe: name, value }, '*');
try { report('parentDocument', parent.document.title); } catch (e) { report('parentDocument', 'blocked'); }
try { report('cookie', document.cookie); } catch (e) { report('cookie', 'blocked'); }
try { localStorage.setItem('k', '1'); report('storage', localStorage.getItem('radicle.theme')); }
catch (e) { report('storage', 'blocked'); }
fetch('${ORIGIN}/api/probe').then(() => report('fetch', 'ok'), () => report('fetch', 'blocked'));
const x = new XMLHttpRequest();
x.onload = () => report('xhr', 'ok');
x.onerror = () => report('xhr', 'blocked');
try { x.open('GET', '${ORIGIN}/api/probe'); x.send(); } catch (e) { report('xhr', 'blocked'); }
const img = new Image();
img.onload = () => report('image', 'ok');
img.onerror = () => report('image', 'blocked');
img.src = '${ORIGIN}/api/probe.png';
addEventListener('message', () => report('theme', getComputedStyle(document.documentElement).getPropertyValue('--rdc-text')));
</script>`;

const LIGHT = { mode: 'light' as const, reducedMotion: false, tokens: { '--rdc-text': '#111827' } };

test('a visual reaches neither the page nor the network', async ({ page }) => {
  let reached = 0;
  await page.route(`${ORIGIN}/api/**`, (route) => {
    reached += 1;
    return route.fulfill({ status: 200, body: 'secret' });
  });
  await page.route(`${ORIGIN}/`, (route) =>
    route.fulfill({
      contentType: 'text/html',
      headers: { 'Set-Cookie': 'radicle_session=secret; Path=/' },
      body: '<!doctype html><title>Folio secreto</title><body></body>',
    }),
  );
  await page.goto(`${ORIGIN}/`);
  await page.evaluate(() => localStorage.setItem('radicle.theme', 'dark'));

  const srcdoc = visualDocument(PROBE, LIGHT);
  await page.evaluate(
    ({ srcdoc, sandbox, height }) => {
      const w = window as unknown as { probes: Record<string, string>; heights: number[] };
      w.probes = {};
      w.heights = [];
      addEventListener('message', (e) => {
        if (e.data?.probe) w.probes[e.data.probe] = e.data.value;
        if (e.data?.type === height) w.heights.push(e.data.height);
      });
      const frame = document.createElement('iframe');
      frame.setAttribute('sandbox', sandbox);
      frame.srcdoc = srcdoc;
      document.body.append(frame);
    },
    { srcdoc, sandbox: VISUAL_SANDBOX, height: HEIGHT_MESSAGE },
  );

  const probes = () => page.evaluate(() => (window as unknown as { probes: object }).probes);
  await expect.poll(async () => Object.keys(await probes()).length).toBeGreaterThanOrEqual(6);
  expect(await probes()).toMatchObject({
    parentDocument: 'blocked',
    cookie: 'blocked',
    storage: 'blocked',
    fetch: 'blocked',
    xhr: 'blocked',
    image: 'blocked',
  });
  expect(reached).toBe(0);

  // It reports its height, and the theme the page sends applies without a reload.
  const heights = () => page.evaluate(() => (window as unknown as { heights: number[] }).heights);
  await expect.poll(async () => Math.max(0, ...(await heights()))).toBeGreaterThanOrEqual(420);
  await page.evaluate((type) => {
    const frame = document.querySelector('iframe') as HTMLIFrameElement;
    frame.contentWindow?.postMessage(
      { type, mode: 'dark', reducedMotion: true, tokens: { '--rdc-text': '#E6E6E6' } },
      '*',
    );
  }, THEME_MESSAGE);
  await expect.poll(async () => ((await probes()) as { theme?: string }).theme).toBe('#E6E6E6');
});
