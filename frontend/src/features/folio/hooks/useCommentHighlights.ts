import { type RefObject, useEffect } from 'react';
import type { FolioThread } from '../../../services/api/folioComments';
import { rangeOf } from './textAnchor';

const NAME = 'folio-comment';

type Highlights = { set: (name: string, h: unknown) => void; delete: (name: string) => void };
type HighlightCtor = new (...ranges: Range[]) => unknown;

/** Paints the text that open inline threads point at, without touching React's DOM: the
 * CSS Custom Highlight API. Browsers without it simply show no highlight. */
export function useCommentHighlights(
  container: RefObject<HTMLElement | null>,
  threads: FolioThread[] | undefined,
  /** Changes when the content does, so the ranges are found again. */
  version: unknown,
): void {
  useEffect(() => {
    const css = (globalThis as { CSS?: { highlights?: Highlights } }).CSS;
    const Highlight = (globalThis as { Highlight?: HighlightCtor }).Highlight;
    const root = container.current;
    if (!css?.highlights || !Highlight || !root) return;
    const ranges = (threads ?? [])
      .filter((t) => t.anchor && !t.orphaned && t.resolved_at == null)
      .map((t) => rangeOf(root, t.anchor!.quote))
      .filter((r): r is Range => r !== null);
    css.highlights.set(NAME, new Highlight(...ranges));
    return () => css.highlights?.delete(NAME);
  }, [container, threads, version]);
}
