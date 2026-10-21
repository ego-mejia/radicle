import type { Citation } from '../../../../services/api/folioChat';

/** `[n]` in the answer becomes a link to the section it cites. */
export function linkCitations(text: string, citations: Citation[]): string {
  const byN = new Map(citations.map((c) => [c.n, c]));
  return text.replace(/\[(\d{1,2})\]/g, (whole, n: string) => {
    const c = byN.get(Number(n));
    return c ? `[\\[${n}\\]](${c.url})` : whole;
  });
}

/** `/folio/p/{id}-{slug}#anchor` → `{id}-{slug}`, the route's page param. */
export function pageOf(url: string): string {
  return url.split('#')[0]!.replace(/^\/folio\/p\//, '');
}
