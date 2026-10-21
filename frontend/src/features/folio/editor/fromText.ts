import type { JSONContent } from '@tiptap/core';

const BULLET = /^\s*[-*•]\s+/;

/** The AI's short Markdown (paragraphs and bullet lists) as editor nodes. Formatting marks
 * like ** are dropped: the proposal is shown first, so nothing surprising lands in the page. */
export function fromText(text: string): JSONContent[] {
  const plain = (s: string) => s.replace(/(\*\*|__|`)/g, '').trim();
  const out: JSONContent[] = [];
  for (const chunk of text.split(/\n\s*\n/)) {
    const lines = chunk.split('\n').filter((l) => l.trim());
    if (!lines.length) continue;
    if (lines.every((l) => BULLET.test(l))) {
      out.push({
        type: 'bulletList',
        content: lines.map((l) => ({
          type: 'listItem',
          content: [
            { type: 'paragraph', content: [{ type: 'text', text: plain(l.replace(BULLET, '')) }] },
          ],
        })),
      });
    } else {
      const words = plain(lines.join(' ').replace(/^#+\s*/, ''));
      if (words) out.push({ type: 'paragraph', content: [{ type: 'text', text: words }] });
    }
  }
  return out;
}
