// A database's view inside a page (Folio 3.6). The `/` menu inserts it empty and its
// node view asks which database and view; until one is chosen it isn't saved.

import { mergeAttributes, Node } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { DatabaseBlock } from '../components/DatabaseBlock';

export const DatabaseViewNode = Node.create({
  name: 'databaseView',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,
  addAttributes: () => ({
    database: { default: null },
    view: { default: null },
  }),
  parseHTML: () => [
    {
      tag: 'div[data-folio="database-view"]',
      getAttrs: (el) => ({
        database: (el as HTMLElement).getAttribute('data-database'),
        view: (el as HTMLElement).getAttribute('data-view'),
      }),
    },
  ],
  renderHTML: ({ HTMLAttributes, node }) => [
    'div',
    mergeAttributes(HTMLAttributes, {
      'data-folio': 'database-view',
      ...(node.attrs.database ? { 'data-database': node.attrs.database } : {}),
      ...(node.attrs.view ? { 'data-view': node.attrs.view } : {}),
    }),
  ],
  addNodeView: () => ReactNodeViewRenderer(DatabaseBlock),
});
