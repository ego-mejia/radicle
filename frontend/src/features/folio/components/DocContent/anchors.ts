// Section anchors exactly as the backend computes them (folio/services/chunking.py), so
// links from search (`#conecta-un-agente`) land on the right heading.

export type DocMark = { type: string; attrs?: Record<string, unknown> | null };

export type DocNode = {
  type: string;
  attrs?: Record<string, unknown> | null;
  content?: DocNode[];
  text?: string;
  marks?: DocMark[];
};

export type Heading = { level: number; text: string; anchor: string };

/** The visible text of inline content (mentions as @handle, statuses by their text). */
export function plainText(nodes: DocNode[] = []): string {
  return nodes
    .map((n) => {
      if (n.type === 'text') return n.text ?? '';
      if (n.type === 'mention') return `@${String(n.attrs?.handle ?? '')}`;
      if (n.type === 'status') return String(n.attrs?.text ?? '');
      if (n.type === 'hardBreak') return ' ';
      return plainText(n.content);
    })
    .join('');
}

export function anchorFor(text: string, taken: Set<string>): string {
  // NFKD splits accents off their letters; dropping non-ASCII keeps the bare letters.
  const ascii = text.normalize('NFKD').replace(/[^\x20-\x7E]/g, '');
  const base =
    ascii
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '') || 'section';
  let anchor = base;
  for (let n = 2; taken.has(anchor); n += 1) anchor = `${base}-${n}`;
  taken.add(anchor);
  return anchor;
}

/** The document's top-level headings with their anchors, in order. */
export function headingsOf(doc: DocNode | null | undefined): Heading[] {
  const taken = new Set<string>();
  return (doc?.content ?? [])
    .filter((n) => n.type === 'heading')
    .map((n) => {
      const text = plainText(n.content);
      return { level: Number(n.attrs?.level ?? 1), text, anchor: anchorFor(text, taken) };
    });
}

/** Words in the document, for the reading time. */
export function wordCount(doc: DocNode | null | undefined): number {
  const walk = (nodes: DocNode[] = []): number =>
    nodes.reduce((sum, n) => {
      if (n.type !== 'text') return sum + walk(n.content);
      return sum + (n.text ?? '').split(/\s+/).filter(Boolean).length;
    }, 0);
  return walk(doc?.content);
}

/** Minutes to read at 220 words a minute, at least one. */
export function readingMinutes(doc: DocNode | null | undefined): number {
  return Math.max(1, Math.round(wordCount(doc) / 220));
}
