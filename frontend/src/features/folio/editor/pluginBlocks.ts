// Blocks that plugins bring (Folio 5.7, ADR 0043). The `/` menu lists those of the
// plugins that are on; usePluginBlocks keeps this list current while someone writes.

import { mergeAttributes, Node } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import type { PluginBlock } from '../../../services/api/plugins';
import { PluginBlockEditor } from '../components/PluginBlockEditor';
import type { BlockItem } from './blocks';

let items: BlockItem[] = [];

/** The `/` menu entries for these plugin blocks, each starting with its defaults. */
export function setPluginBlocks(blocks: PluginBlock[]): void {
  items = blocks.map((b) => ({
    key: `plugin:${b.id}`,
    label: `${b.icon ? `${b.icon} ` : ''}${b.name}`,
    keywords: `plugin ${b.name} ${b.description} ${b.type}`,
    run: (c) =>
      c.insertContent({
        type: 'pluginBlock',
        attrs: {
          plugin: b.plugin,
          block: b.type,
          data: Object.fromEntries(
            b.fields.filter((f) => f.default).map((f) => [f.key, f.default]),
          ),
        },
      }),
  }));
}

export function pluginBlockItems(): BlockItem[] {
  return items;
}

/** What a block's HTML gets before its own code: its values as window.radicle.data and the
 * reader's language (en, es) as window.radicle.lang. The sandbox can't read the app's. */
export function pluginCode(html: string, data: Record<string, string>, lang = 'en'): string {
  const json = JSON.stringify({ data, lang }).replace(/</g, '\\u003c');
  return `<script>window.radicle=${json};</script>${html}`;
}

export const PluginBlockNode = Node.create({
  name: 'pluginBlock',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,
  addAttributes: () => ({
    plugin: {
      default: null,
      parseHTML: (el) => el.getAttribute('data-plugin'),
      renderHTML: (a) => (a.plugin ? { 'data-plugin': a.plugin } : {}),
    },
    block: {
      default: null,
      parseHTML: (el) => el.getAttribute('data-block'),
      renderHTML: (a) => (a.block ? { 'data-block': a.block } : {}),
    },
    data: {
      default: null,
      parseHTML: (el) => {
        const raw = el.getAttribute('data-values');
        return raw ? (JSON.parse(raw) as Record<string, string>) : null;
      },
      renderHTML: (a) => (a.data ? { 'data-values': JSON.stringify(a.data) } : {}),
    },
  }),
  parseHTML: () => [{ tag: 'div[data-folio="plugin"]' }],
  renderHTML: ({ HTMLAttributes }) => [
    'div',
    mergeAttributes(HTMLAttributes, { 'data-folio': 'plugin' }),
  ],
  addNodeView: () => ReactNodeViewRenderer(PluginBlockEditor),
});
