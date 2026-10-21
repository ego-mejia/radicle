// The document a Visual block runs in (Folio 3.3, docs/folio/fase-3.md). It lives in a
// sandboxed iframe without allow-same-origin, so its origin is opaque: no cookies, no
// storage and no access to the page. The CSP blocks the network. The page sends the theme
// with postMessage and the visual reports its height the same way.
// No imports from the app: the end-to-end sandbox test loads this file in a bare browser.

export const VISUAL_CSP =
  "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; " +
  'img-src data: blob:; font-src data:';
export const VISUAL_SANDBOX = 'allow-scripts';
export const MAX_HEIGHT = 2000;

/** The page → visual message with the theme; the visual → page one with its height. */
export const THEME_MESSAGE = 'radicle:theme';
export const HEIGHT_MESSAGE = 'radicle:height';

export type VisualTheme = {
  mode: 'light' | 'dark';
  reducedMotion: boolean;
  /** CSS variables, `--rdc-*`. */
  tokens: Record<string, string>;
};

function rules(tokens: Record<string, string>): string {
  return Object.entries(tokens)
    .map(([name, value]) => `${name}:${value.replace(/[;{}<]/g, '')}`)
    .join(';');
}

// Runs before the visual's own code: applies the theme the page sends and reports the
// height whenever it changes.
const HOST_SCRIPT = `(() => {
  const root = document.documentElement;
  const style = document.getElementById('rdc-tokens');
  addEventListener('message', (e) => {
    const d = e.data;
    if (e.source !== parent || !d || d.type !== '${THEME_MESSAGE}') return;
    root.dataset.theme = d.mode;
    root.dataset.reducedMotion = String(Boolean(d.reducedMotion));
    style.textContent = ':root{' + Object.entries(d.tokens || {})
      .map(([k, v]) => k + ':' + String(v).replace(/[;{}<]/g, '')).join(';') + '}';
  });
  // The body's height, not the root's: the root is never shorter than the iframe, so a
  // frame that grew once (say, while narrow) could never shrink back.
  let last = 0;
  const report = () => {
    const h = Math.ceil(document.body ? document.body.scrollHeight : root.scrollHeight);
    if (h !== last) { last = h; parent.postMessage({ type: '${HEIGHT_MESSAGE}', height: h }, '*'); }
  };
  addEventListener('load', report);
  const sizes = new ResizeObserver(report);
  sizes.observe(root);
  addEventListener('DOMContentLoaded', () => sizes.observe(document.body));
})();`;

// The color-scheme follows the theme: when it differs from the page's, Chrome paints the
// iframe opaque white behind a transparent visual.
const BASE =
  ':root[data-theme="dark"]{color-scheme:dark}:root[data-theme="light"]{color-scheme:light}' +
  'html,body{margin:0;background:transparent;color:var(--rdc-text);' +
  'font-family:var(--rdc-font)}svg{display:block;max-width:100%;height:auto}' +
  '[data-reduced-motion="true"] *{animation:none!important;transition:none!important}';

/** The iframe's srcdoc: the policy first, then the theme, the host script and the code. */
export function visualDocument(code: string, theme: VisualTheme): string {
  return [
    '<!doctype html>',
    `<html data-theme="${theme.mode}" data-reduced-motion="${theme.reducedMotion}">`,
    '<head><meta charset="utf-8">',
    `<meta http-equiv="Content-Security-Policy" content="${VISUAL_CSP}">`,
    `<style>${BASE}</style>`,
    `<style id="rdc-tokens">:root{${rules(theme.tokens)}}</style>`,
    `<script>${HOST_SCRIPT}</script>`,
    `</head><body>${code}</body></html>`,
  ].join('');
}
