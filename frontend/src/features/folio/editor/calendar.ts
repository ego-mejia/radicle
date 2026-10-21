// A calendar inside a page (Folio 5.8). The `/` menu inserts it empty and its node view
// asks which calendar; until one is chosen it isn't saved.

import { mergeAttributes, Node } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { CalendarBlock } from '../components/CalendarBlock';

export const CalendarNode = Node.create({
  name: 'calendar',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,
  addAttributes: () => ({
    calendar: { default: null },
    view: { default: null },
  }),
  parseHTML: () => [
    {
      tag: 'div[data-folio="calendar"]',
      getAttrs: (el) => ({
        calendar: (el as HTMLElement).getAttribute('data-calendar'),
        view: (el as HTMLElement).getAttribute('data-view'),
      }),
    },
  ],
  renderHTML: ({ HTMLAttributes, node }) => [
    'div',
    mergeAttributes(HTMLAttributes, {
      'data-folio': 'calendar',
      ...(node.attrs.calendar ? { 'data-calendar': node.attrs.calendar } : {}),
      ...(node.attrs.view ? { 'data-view': node.attrs.view } : {}),
    }),
  ],
  addNodeView: () => ReactNodeViewRenderer(CalendarBlock),
});
