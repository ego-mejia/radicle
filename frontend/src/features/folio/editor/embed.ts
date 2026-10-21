// A pasted link as a block (Folio 3.7): the same card or embed the reader shows. Pasting a
// lone http(s) link into an empty paragraph turns it into one.

import { mergeAttributes, Node } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { EmbedNodeView } from '../components/EmbedNodeView';

const LONE_LINK = /^https?:\/\/\S+$/;

/** A single http(s) link, as pasted text. */
export function loneLink(text: string): string | null {
  const trimmed = text.trim();
  return LONE_LINK.test(trimmed) ? trimmed : null;
}

export const Embed = Node.create({
  name: 'embed',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,
  addAttributes: () => ({
    url: { default: null },
    title: { default: null },
    provider: { default: null },
  }),
  parseHTML: () => [
    {
      tag: 'div[data-folio="embed"]',
      getAttrs: (el) => ({
        url: (el as HTMLElement).getAttribute('data-url'),
        title: (el as HTMLElement).getAttribute('data-title'),
      }),
    },
  ],
  renderHTML: ({ HTMLAttributes, node }) => [
    'div',
    mergeAttributes(HTMLAttributes, {
      'data-folio': 'embed',
      'data-url': node.attrs.url,
      ...(node.attrs.title ? { 'data-title': node.attrs.title } : {}),
    }),
    ['a', { href: node.attrs.url }, String(node.attrs.title ?? node.attrs.url)],
  ],
  addNodeView: () => ReactNodeViewRenderer(EmbedNodeView),
  addProseMirrorPlugins() {
    const type = this.type;
    return [
      new Plugin({
        key: new PluginKey('folioEmbedPaste'),
        props: {
          handlePaste: (view, event) => {
            const url = loneLink(event.clipboardData?.getData('text/plain') ?? '');
            const { $from, empty } = view.state.selection;
            const parent = $from.parent;
            if (!url || !empty || parent.type.name !== 'paragraph' || parent.content.size > 0) {
              return false;
            }
            const block = type.create({ url });
            view.dispatch(view.state.tr.replaceWith($from.before(), $from.after(), block));
            return true;
          },
        },
      }),
    ];
  },
});
