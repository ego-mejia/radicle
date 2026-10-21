// Folio's blocks that StarterKit lacks, with the same names and attributes as the server's
// schema. Each renders plain HTML with data attributes; the editor styles them.

import { InputRule, mergeAttributes, Node } from '@tiptap/core';
import type { DOMOutputSpec } from '@tiptap/pm/model';
import { assetUrl } from '../../../services/api/folio';
import type { ColumnLayout, PanelKind, StatusColor } from './schema';

/** `assetId` → `data-asset-id`. */
const htmlName = (key: string) => `data-${key.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}`;

/** An attribute stored in the document and mirrored to a `data-*` attribute. */
function data(key: string, fallback: unknown = null) {
  return {
    default: fallback,
    parseHTML: (el: HTMLElement) => el.getAttribute(htmlName(key)) ?? fallback,
    renderHTML: (attrs: Record<string, unknown>) =>
      attrs[key] === null || attrs[key] === undefined ? {} : { [htmlName(key)]: attrs[key] },
  };
}

function numeric(key: string) {
  return {
    default: null,
    parseHTML: (el: HTMLElement) => {
      const raw = el.getAttribute(htmlName(key));
      return raw === null ? null : Number(raw);
    },
    renderHTML: (attrs: Record<string, unknown>) =>
      attrs[key] === null ? {} : { [htmlName(key)]: String(attrs[key]) },
  };
}

function container(name: string, attrs: Record<string, ReturnType<typeof data>>) {
  return Node.create({
    name,
    group: 'block',
    content: 'block+',
    defining: true,
    addAttributes: () => attrs,
    parseHTML: () => [{ tag: `div[data-folio="${name}"]` }],
    renderHTML: ({ HTMLAttributes }) => [
      'div',
      mergeAttributes(HTMLAttributes, { 'data-folio': name }),
      0,
    ],
  });
}

export const Panel = container('panel', { kind: data('kind', 'info' satisfies PanelKind) });
export const Expand = container('expand', { title: data('title', '') });

export const Columns = Node.create({
  name: 'columns',
  group: 'block',
  content: 'column{2,3}',
  isolating: true,
  addAttributes: () => ({ layout: data('layout', 'two' satisfies ColumnLayout) }),
  parseHTML: () => [{ tag: 'div[data-folio="columns"]' }],
  renderHTML: ({ HTMLAttributes }) => [
    'div',
    mergeAttributes(HTMLAttributes, { 'data-folio': 'columns' }),
    0,
  ],
});

export const Column = Node.create({
  name: 'column',
  content: 'block+',
  isolating: true,
  parseHTML: () => [{ tag: 'div[data-folio="column"]' }],
  renderHTML: ({ HTMLAttributes }) => [
    'div',
    mergeAttributes(HTMLAttributes, { 'data-folio': 'column' }),
    0,
  ],
});

/** A block with no content of its own, like the table of contents. */
type Attrs = Record<string, unknown>;
type Inner = (attrs: Attrs) => DOMOutputSpec[];

/** A block with no content of its own, like the table of contents; `inner` draws it. */
function atom(name: string, attrs: Record<string, ReturnType<typeof data>> = {}, inner?: Inner) {
  return Node.create({
    name,
    group: 'block',
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes: () => attrs,
    parseHTML: () => [{ tag: `div[data-folio="${name}"]` }],
    renderHTML: ({ node, HTMLAttributes }) => [
      'div',
      mergeAttributes(HTMLAttributes, { 'data-folio': name }),
      ...(inner?.(node.attrs) ?? []),
    ],
  });
}

/** Uploaded media point at the asset; linked media keep their own src. */
const source = (attrs: Attrs) =>
  typeof attrs.src === 'string' ? attrs.src : attrs.assetId ? assetUrl(String(attrs.assetId)) : '';

const caption = (attrs: Attrs): DOMOutputSpec[] =>
  attrs.caption ? [['span', { class: 'caption' }, String(attrs.caption)]] : [];

export const TableOfContents = atom('tableOfContents');
export const ChildPages = atom('childPages');
export const Image = atom(
  'image',
  {
    assetId: data('assetId'),
    src: data('src'),
    alt: data('alt'),
    caption: data('caption'),
    size: data('size'),
    align: data('align'),
  },
  (attrs) => [['img', { src: source(attrs), alt: String(attrs.alt ?? '') }], ...caption(attrs)],
);
export const File = atom(
  'file',
  {
    assetId: data('assetId'),
    name: data('name', ''),
    mimeType: data('mimeType'),
    size: numeric('size'),
  },
  (attrs) => [['a', { href: source(attrs), download: String(attrs.name) }, String(attrs.name)]],
);
export const Video = atom(
  'video',
  { assetId: data('assetId'), src: data('src'), caption: data('caption') },
  (attrs) => [['video', { src: source(attrs), controls: 'true' }], ...caption(attrs)],
);

function inlineAtom(name: string, attrs: Record<string, ReturnType<typeof data>>, label: string) {
  return Node.create({
    name,
    group: 'inline',
    inline: true,
    atom: true,
    selectable: true,
    addAttributes: () => attrs,
    parseHTML: () => [{ tag: `span[data-folio="${name}"]` }],
    renderHTML: ({ node, HTMLAttributes }) => [
      'span',
      mergeAttributes(HTMLAttributes, { 'data-folio': name }),
      label === 'handle' ? `@${String(node.attrs.handle)}` : String(node.attrs[label] ?? ''),
    ],
    renderText: ({ node }) =>
      label === 'handle' ? `@${String(node.attrs.handle)}` : String(node.attrs[label] ?? ''),
  });
}

// `@handle ` turns into a mention when you type the space after it.
export const Mention = inlineAtom('mention', { handle: data('handle', '') }, 'handle').extend({
  addInputRules() {
    return [
      new InputRule({
        find: /(?:^|\s)@([a-z0-9][a-z0-9_-]{0,63}) $/,
        handler: ({ state, range, match }) => {
          const start = range.from + match[0].indexOf('@');
          state.tr.replaceWith(start, range.to, [
            this.type.create({ handle: match[1] }),
            state.schema.text(' '),
          ]);
        },
      }),
    ];
  },
});
export const Status = inlineAtom(
  'status',
  { text: data('text', ''), color: data('color', 'grey' satisfies StatusColor) },
  'text',
);
