// Charts and timelines edited as text, in the same shapes Markdown uses for them
// (docs/folio/markdown.md): a chart is rows of cells split by |, a timeline one
// milestone per line, `[x] date | title | text`.

import type { ChartData } from '../../../ChartBlock/tableData';
import type { TimelineItem } from '../../../Timeline';

export function chartToText(data: ChartData | null | undefined): string {
  return (data ?? []).map((row) => row.join(' | ')).join('\n');
}

export function textToChart(text: string): ChartData {
  const rows = text
    .split('\n')
    .filter((line) => line.trim())
    .map((line) => line.split('|').map((c) => c.trim()));
  const width = rows[0]?.length ?? 0;
  return rows.map((row, i) => {
    const cells = [...row.slice(0, width), ...Array(Math.max(0, width - row.length)).fill('')];
    if (i === 0) return cells;
    return cells.map((c, j) => (j === 0 ? c : Number(c.replace(/,/g, '')) || 0));
  });
}

const BOXES = { done: '[x] ', in_progress: '[~] ', planned: '[ ] ' } as const;
const STATUS: Record<string, TimelineItem['status']> = {
  x: 'done',
  '~': 'in_progress',
  ' ': 'planned',
};

export function timelineToText(items: TimelineItem[] | null | undefined): string {
  return (items ?? [])
    .map(
      (i) =>
        (i.status ? BOXES[i.status] : '') +
        [i.date ?? '', i.title, i.text ?? ''].join(' | ').replace(/( \| )+$/, ''),
    )
    .join('\n');
}

export function textToTimeline(text: string): TimelineItem[] {
  return text
    .split('\n')
    .filter((line) => line.trim())
    .flatMap((raw) => {
      const box = /^\[([ x~])\]\s*/.exec(raw.trim());
      const line = box ? raw.trim().slice(box[0].length) : raw;
      const parts = line.split('|').map((p) => p.trim());
      const [date, title, ...rest] = parts.length === 1 ? ['', parts[0] ?? ''] : parts;
      if (!title) return [];
      const item: TimelineItem = { title };
      if (date) item.date = date;
      if (rest.join(' | ')) item.text = rest.join(' | ');
      const status = box ? STATUS[box[1] ?? ''] : undefined;
      if (status) item.status = status;
      return [item];
    });
}
