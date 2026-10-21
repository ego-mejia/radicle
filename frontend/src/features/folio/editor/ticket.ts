// A Docket ticket's smart link (Folio 4.1). Pasting a key (PA-4) or a Docket ticket link
// turns it into one; its status and assignee are read live, never stored.

import { mergeAttributes, Node } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { TicketNodeView } from '../components/TicketNodeView';
import { ticketKeyIn } from '../../../services/api/folioTickets';

export const TicketLink = Node.create({
  name: 'ticket',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,
  addAttributes: () => ({ key: { default: '' } }),
  parseHTML: () => [
    {
      tag: 'span[data-folio="ticket"]',
      getAttrs: (el) => ({ key: (el as HTMLElement).getAttribute('data-key') }),
    },
  ],
  renderHTML: ({ node, HTMLAttributes }) => [
    'span',
    mergeAttributes(HTMLAttributes, { 'data-folio': 'ticket', 'data-key': node.attrs.key }),
    String(node.attrs.key),
  ],
  renderText: ({ node }) => String(node.attrs.key),
  addNodeView: () => ReactNodeViewRenderer(TicketNodeView),
  addProseMirrorPlugins() {
    const type = this.type;
    return [
      new Plugin({
        key: new PluginKey('folioTicketPaste'),
        props: {
          handlePaste: (view, event) => {
            const key = ticketKeyIn(event.clipboardData?.getData('text/plain') ?? '');
            if (!key || view.state.selection.$from.parent.type.spec.code) return false;
            view.dispatch(view.state.tr.replaceSelectionWith(type.create({ key }), false));
            return true;
          },
        },
      }),
    ];
  },
});
