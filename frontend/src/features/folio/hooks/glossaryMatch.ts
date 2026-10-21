import type { GlossaryTerm } from '../../../services/api/folioAi';

export type Match = { term: GlossaryTerm; range: Range };

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** The first place each approved term (or one of its aliases) appears as a whole word in
 * `container`'s text, as DOM ranges. Longer names win, so "Folio MCP" beats "Folio". */
export function glossaryMatches(container: HTMLElement, terms: GlossaryTerm[]): Match[] {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const nodes: Text[] = [];
  let text = '';
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    nodes.push(n as Text);
    text += (n as Text).data;
  }
  const locate = (pos: number, end: boolean): [Text, number] | null => {
    let seen = 0;
    for (const node of nodes) {
      const next = seen + node.data.length;
      if (pos < next || (end && pos === next)) return [node, pos - seen];
      seen = next;
    }
    return null;
  };
  const names = terms
    .flatMap((term) => [term.term, ...term.aliases].map((name) => ({ term, name })))
    .filter((n) => n.name.trim())
    .sort((a, b) => b.name.length - a.name.length);
  const taken: [number, number][] = [];
  const found = new Map<string, Match>();
  for (const { term, name } of names) {
    if (found.has(term.id)) continue;
    const re = new RegExp(`(?<![\\p{L}\\p{N}])${escape(name)}(?![\\p{L}\\p{N}])`, 'giu');
    for (const m of text.matchAll(re)) {
      const [at, end] = [m.index, m.index + m[0].length];
      if (taken.some(([s, e]) => at < e && end > s)) continue;
      const from = locate(at, false);
      const to = locate(end, true);
      if (!from || !to) break;
      const range = document.createRange();
      range.setStart(...from);
      range.setEnd(...to);
      found.set(term.id, { term, range });
      taken.push([at, end]);
      break;
    }
  }
  return [...found.values()];
}
