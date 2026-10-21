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
