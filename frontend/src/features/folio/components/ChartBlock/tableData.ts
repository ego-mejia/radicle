import type { DocNode } from '../DocContent/anchors';

export type ChartData = (string | number)[][];

function textOf(node: DocNode): string {
  if (node.type === 'text') return node.text ?? '';
  return (node.content ?? []).map(textOf).join(node.type === 'paragraph' ? '' : ' ');
}

/** A number as people write it in a table: thousands commas, missing as 0. */
function numberOf(cell: string): number {
  const n = Number(cell.replace(/,/g, '').trim());
  return Number.isFinite(n) ? n : 0;
}

/** The rows of a document table as chart data: the first row names the columns, the
 * first column holds the labels and the rest numbers (like the server's chart data). */
export function tableData(table: DocNode | undefined): ChartData | null {
  if (table?.type !== 'table') return null;
  const rows = (table.content ?? []).map((row) => (row.content ?? []).map((c) => textOf(c).trim()));
  const width = rows[0]?.length ?? 0;
  if (rows.length < 2 || width < 2) return null;
  return [
    rows[0] ?? [],
    ...rows.slice(1).map((r) => [r[0] ?? '', ...r.slice(1, width).map(numberOf)]),
  ];
}
