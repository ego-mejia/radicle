// The blocks the `/` menu inserts. Labels live in i18n under folio.editor.blocks.<key>.

import type { ChainedCommands, JSONContent } from '@tiptap/core';
import { newItemId } from './actionItem';
import type { PanelKind } from './schema';

export type BlockItem = {
  key: string;
  /** Extra words that find it, in both languages. */
  keywords: string;
  run: (chain: ChainedCommands) => ChainedCommands;
};

const paragraph: JSONContent = { type: 'paragraph' };

/** What a new visual starts with: the tokens, so it already follows the theme. */
export const VISUAL_STARTER =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 120">' +
  '<rect width="400" height="120" rx="10" fill="var(--rdc-surface)" stroke="var(--rdc-border)"/>' +
  '<circle cx="60" cy="60" r="28" fill="var(--rdc-accent-fill)"/>' +
  '<text x="110" y="66" font-family="var(--rdc-font)" font-size="18" fill="var(--rdc-text)">' +
  'Visual</text></svg>';
const column: JSONContent = { type: 'column', content: [paragraph] };

const panel = (kind: PanelKind): BlockItem => ({
  key: `panel_${kind}`,
  keywords: `panel callout aviso ${kind}`,
  run: (c) => c.insertContent({ type: 'panel', attrs: { kind }, content: [paragraph] }),
});

export const BLOCKS: BlockItem[] = [
  { key: 'text', keywords: 'text paragraph texto parrafo', run: (c) => c.setParagraph() },
  { key: 'heading1', keywords: 'h1 heading title titulo', run: (c) => c.setHeading({ level: 1 }) },
  { key: 'heading2', keywords: 'h2 heading subtitulo', run: (c) => c.setHeading({ level: 2 }) },
  { key: 'heading3', keywords: 'h3 heading', run: (c) => c.setHeading({ level: 3 }) },
  { key: 'bullets', keywords: 'ul list bullet lista', run: (c) => c.toggleBulletList() },
  { key: 'numbered', keywords: 'ol list numbered numerada', run: (c) => c.toggleOrderedList() },
  { key: 'tasks', keywords: 'todo task checklist tareas', run: (c) => c.toggleTaskList() },
  {
    key: 'actionItem',
    keywords: 'action item task assign asignar tarea pendiente responsable',
    run: (c) => c.insertContent({ type: 'actionItem', attrs: { id: newItemId(), done: false } }),
  },
  { key: 'quote', keywords: 'quote blockquote cita', run: (c) => c.toggleBlockquote() },
  { key: 'code', keywords: 'code codigo snippet', run: (c) => c.toggleCodeBlock() },
  {
    key: 'table',
    keywords: 'table tabla grid',
    run: (c) => c.insertTable({ rows: 3, cols: 3, withHeaderRow: true }),
  },
  panel('info'),
  panel('tip'),
  panel('warning'),
  panel('error'),
  panel('note'),
  {
    key: 'expand',
    keywords: 'expand toggle collapse desplegable',
    run: (c) => c.insertContent({ type: 'expand', attrs: { title: '' }, content: [paragraph] }),
  },
  {
    key: 'columns2',
    keywords: 'columns columnas layout two dos',
    run: (c) =>
      c.insertContent({ type: 'columns', attrs: { layout: 'two' }, content: [column, column] }),
  },
  {
    key: 'columns3',
    keywords: 'columns columnas layout three tres',
    run: (c) =>
      c.insertContent({
        type: 'columns',
        attrs: { layout: 'three' },
        content: [column, column, column],
      }),
  },
  {
    key: 'toc',
    keywords: 'toc contents indice contenido',
    run: (c) => c.insertContent({ type: 'tableOfContents' }),
  },
  {
    key: 'children',
    keywords: 'children child pages hijas paginas',
    run: (c) => c.insertContent({ type: 'childPages' }),
  },
  {
    key: 'status',
    keywords: 'status estado label etiqueta',
    run: (c) => c.insertContent({ type: 'status', attrs: { text: 'TODO', color: 'grey' } }),
  },
  {
    key: 'database',
    keywords: 'database board base de datos tablero inventario',
    run: (c) => c.insertContent({ type: 'databaseView' }),
  },
  {
    key: 'whiteboard',
    keywords: 'whiteboard pizarra dibujo excalidraw diagrama boceto',
    run: (c) => c.insertContent({ type: 'whiteboard' }),
  },
  {
    key: 'visual',
    keywords: 'visual svg html dibujo ilustracion grafico custom',
    run: (c) => c.insertContent({ type: 'visual', attrs: { format: 'svg', code: VISUAL_STARTER } }),
  },
  {
    key: 'diagram',
    keywords: 'diagram mermaid flow flujo diagrama secuencia gantt',
    run: (c) => c.insertContent({ type: 'diagram', attrs: { source: 'flowchart LR\n  A --> B' } }),
  },
  {
    key: 'chart',
    keywords: 'chart graph bar line pie grafica barras lineas pastel',
    run: (c) =>
      c.insertContent({
        type: 'chart',
        attrs: {
          kind: 'bar',
          data: [
            ['', 'Serie'],
            ['A', 1],
            ['B', 2],
          ],
        },
      }),
  },
  {
    key: 'timeline',
    keywords: 'timeline milestones roadmap hitos linea tiempo',
    run: (c) => c.insertContent({ type: 'timeline', attrs: { items: [{ title: 'Hito' }] } }),
  },
  {
    key: 'comparison',
    keywords: 'comparison compare versus comparar comparacion lado',
    run: (c) =>
      c.insertContent({
        type: 'comparison',
        content: [
          { type: 'comparisonSide', content: [paragraph] },
          { type: 'comparisonSide', content: [paragraph] },
        ],
      }),
  },
  {
    key: 'formula',
    keywords: 'formula math latex katex ecuacion matematicas',
    run: (c) => c.insertContent({ type: 'formula', attrs: { latex: 'E = mc^2' } }),
  },
  {
    key: 'inlineFormula',
    keywords: 'inline formula math latex en linea',
    run: (c) => c.insertContent({ type: 'inlineFormula', attrs: { latex: 'x^2' } }),
  },
  {
    key: 'pageList',
    keywords: 'pages label list lista paginas etiqueta',
    run: (c) => c.insertContent({ type: 'pageList', attrs: { label: '' } }),
  },
  {
    key: 'ticketTable',
    keywords: 'tickets docket rql table tabla tareas',
    run: (c) => c.insertContent({ type: 'ticketTable', attrs: { rql: '' } }),
  },
  { key: 'divider', keywords: 'hr divider line separador', run: (c) => c.setHorizontalRule() },
];

/** Blocks whose label or keywords contain every word of the query. */
export function findBlocks(items: BlockItem[], query: string, label: (key: string) => string) {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  return items.filter((item) => {
    const text = `${label(item.key)} ${item.keywords}`.toLowerCase();
    return words.every((word) => text.includes(word));
  });
}
