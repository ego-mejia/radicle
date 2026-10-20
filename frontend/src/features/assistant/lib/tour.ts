import type { components } from '../../../services/api/schema';

export type TourStep = components['schemas']['TourStepOut'];

/** The tour cursor is always white, like a real pointer, in light and dark mode. */
export const CURSOR_FILL = '#FFFFFF';

/** The element a step points at: the first visible one with that data-tour id. */
export function findTarget(target: string): HTMLElement | null {
  const all = document.querySelectorAll<HTMLElement>(`[data-tour="${CSS.escape(target)}"]`);
  return [...all].find((el) => el.getClientRects().length > 0) ?? null;
}

/** Wait until a target shows up (after a navigation or a dialog opening). */
export async function waitForTarget(target: string, timeoutMs = 4000): Promise<HTMLElement | null> {
  const started = Date.now();
  for (;;) {
    const el = findTarget(target);
    if (el) return el;
    if (Date.now() - started > timeoutMs) return null;
    await new Promise((r) => setTimeout(r, 100));
  }
}

/** The page of a step with {project} filled in, or null if it needs no navigation. */
export function pageFor(step: TourStep, project: string | null): string | null {
  if (!step.page) return null;
  if (step.page.includes('{project}'))
    return project ? step.page.replace('{project}', project) : null;
  return step.page;
}

/** The project in the current URL (/p/PA/...). */
export function projectInPath(pathname: string): string | null {
  return /^\/p\/([^/]+)/.exec(pathname)?.[1]?.toUpperCase() ?? null;
}

/** Tell Radi where to look (he follows the tour cursor). */
export function radiLook(x: number, y: number): void {
  window.dispatchEvent(new CustomEvent('radi:look', { detail: { x, y } }));
}
