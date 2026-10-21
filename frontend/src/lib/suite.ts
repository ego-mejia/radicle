/** The apps of the Radicle suite and the last page each one showed, per user. */
export type SuiteApp = 'docket' | 'folio';

export const HOME: Record<SuiteApp, string> = { docket: '/', folio: '/folio' };

export function appOf(pathname: string): SuiteApp {
  return pathname === '/folio' || pathname.startsWith('/folio/') ? 'folio' : 'docket';
}

const storageKey = (app: SuiteApp, handle: string) => `radicle.lastRoute.${app}.${handle}`;

export function rememberRoute(handle: string, href: string): void {
  const app = appOf(href.split(/[?#]/)[0] ?? '/');
  try {
    localStorage.setItem(storageKey(app, handle), href);
  } catch {
    // Private mode or storage full: switching just goes to the app's home.
  }
}

export function lastRoute(app: SuiteApp, handle: string): string {
  try {
    const href = localStorage.getItem(storageKey(app, handle));
    if (href && appOf(href.split(/[?#]/)[0] ?? '/') === app) return href;
  } catch {
    // ignore, as above
  }
  return HOME[app];
}
