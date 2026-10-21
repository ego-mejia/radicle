import { useRouterState } from '@tanstack/react-router';
import { type RefObject, useEffect } from 'react';

const SHOWN_MS = 6000;

/**
 * Opening a page at `#section` (a chat citation, a search result) scrolls to that section
 * and marks its heading and first paragraph with `data-cited` for a few seconds, once the
 * content has rendered.
 */
export function useCitedSection(
  container: RefObject<HTMLElement | null>,
  /** Changes when the content does, so the section is looked for again. */
  version: unknown,
): void {
  const hash = useRouterState({ select: (s) => s.location.hash });
  useEffect(() => {
    const root = container.current;
    const id = decodeURIComponent(hash.replace(/^#/, ''));
    if (!root || !id) return;
    const heading = root.querySelector<HTMLElement>(`[id="${id.replace(/"/g, '')}"]`);
    if (!heading) return;
    heading.scrollIntoView?.({ block: 'start', behavior: 'smooth' });
    const marked = [heading, heading.nextElementSibling].filter(
      (el): el is HTMLElement => el instanceof HTMLElement,
    );
    for (const el of marked) el.dataset.cited = 'true';
    const timer = window.setTimeout(() => {
      for (const el of marked) delete el.dataset.cited;
    }, SHOWN_MS);
    return () => {
      window.clearTimeout(timer);
      for (const el of marked) delete el.dataset.cited;
    };
  }, [container, hash, version]);
}
