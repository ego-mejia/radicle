// A whiteboard inside a page (Folio 3.5). The `/` menu inserts it empty and its node
// view asks which whiteboard; until one is chosen it isn't saved.

import { mergeAttributes, Node } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { WhiteboardBlock } from '../components/WhiteboardBlock';

export const WhiteboardNode = Node.create({
  name: 'whiteboard',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,
  addAttributes: () => ({
    whiteboard: { default: null },
  }),
  parseHTML: () => [
    {
      tag: 'div[data-folio="whiteboard"]',
      getAttrs: (el) => ({ whiteboard: (el as HTMLElement).getAttribute('data-whiteboard') }),
    },
  ],
  renderHTML: ({ HTMLAttributes, node }) => [
    'div',
    mergeAttributes(HTMLAttributes, {
      'data-folio': 'whiteboard',
      ...(node.attrs.whiteboard ? { 'data-whiteboard': node.attrs.whiteboard } : {}),
    }),
  ],
  addNodeView: () => ReactNodeViewRenderer(WhiteboardBlock),
});
