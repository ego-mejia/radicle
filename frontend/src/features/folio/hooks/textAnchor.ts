import type { FolioAnchor } from '../../../services/api/folioComments';

const CONTEXT = 32;

function offsetIn(container: Node, node: Node, offset: number): number {
  const range = document.createRange();
  range.setStart(container, 0);
  range.setEnd(node, offset);
  return range.toString().length;
}

/** The selection inside `container` as a comment anchor: the quote, a little context on
 * each side and where it starts. The server finds it again in the page's text. */
export function anchorFromSelection(
  container: HTMLElement,
  selection: Selection | null,
): FolioAnchor | null {
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) return null;
  const range = selection.getRangeAt(0);
  if (!container.contains(range.commonAncestorContainer)) return null;
  const quote = range.toString().trim();
  if (!quote) return null;
  const text = container.textContent ?? '';
  const raw = offsetIn(container, range.startContainer, range.startOffset);
  const start = raw + (range.toString().length - range.toString().trimStart().length);
  const end = start + quote.length;
  return {
    quote,
    prefix: text.slice(Math.max(0, start - CONTEXT), start),
    suffix: text.slice(end, end + CONTEXT),
    offset: start,
  };
}

/** A DOM range over the first occurrence of `quote` in `container`'s text, or null. */
export function rangeOf(container: HTMLElement, quote: string): Range | null {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  let text = '';
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    nodes.push(n as Text);
    text += (n as Text).data;
  }
  const at = quote ? text.indexOf(quote) : -1;
  if (at < 0) return null;
  const locate = (pos: number, end: boolean): [Text, number] | null => {
    let seen = 0;
    for (const node of nodes) {
      const next = seen + node.data.length;
      if (pos < next || (end && pos === next)) return [node, pos - seen];
      seen = next;
    }
    return null;
  };
  const from = locate(at, false);
  const to = locate(at + quote.length, true);
  if (!from || !to) return null;
  const range = document.createRange();
  range.setStart(...from);
  range.setEnd(...to);
  return range;
}

/** The anchor of the last heading before the selection inside `container`: the section a
 * ticket made from it links to. The reader's headings carry it as their id; the editor's
 * don't, so it passes the document's anchors in order (`headingsOf`). Null before the
 * first heading. */
export function sectionOf(
  container: HTMLElement,
  selection: Selection | null,
  anchors: string[] = [],
): string | null {
  if (!selection || selection.rangeCount === 0) return null;
  const start = selection.getRangeAt(0).startContainer;
  let found: string | null = null;
  const headings = container.querySelectorAll<HTMLElement>('h1, h2, h3, h4');
  headings.forEach((heading, i) => {
    const before = heading.compareDocumentPosition(start) & Node.DOCUMENT_POSITION_FOLLOWING;
    if (before || heading.contains(start)) found = heading.id || anchors[i] || found;
  });
  return found;
}
