// Builders for Folio documents in tests, like backend/tests/unit/folio_docs.py.
import type { DocNode } from './anchors';

export const t = (text: string, ...marks: string[]): DocNode => ({
  type: 'text',
  text,
  ...(marks.length ? { marks: marks.map((m) => ({ type: m })) } : {}),
});

export const p = (...content: DocNode[]): DocNode => ({ type: 'paragraph', content });

export const b = (
  type: string,
  attrs: Record<string, unknown>,
  ...content: DocNode[]
): DocNode => ({
  type,
  attrs,
  ...(content.length ? { content } : {}),
});

export const doc = (...content: DocNode[]): DocNode => ({ type: 'doc', content });
