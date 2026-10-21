// Folio's blocks that StarterKit lacks, with the same names and attributes as the server's
// schema. Each renders plain HTML with data attributes; the editor styles them.

import { mergeAttributes, Node } from '@tiptap/core';
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
function atom(name: string, attrs: Record<string, ReturnType<typeof data>> = {}) {
  return Node.create({
    name,
    group: 'block',
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes: () => attrs,
    parseHTML: () => [{ tag: `div[data-folio="${name}"]` }],
    renderHTML: ({ HTMLAttributes }) => [
      'div',
      mergeAttributes(HTMLAttributes, { 'data-folio': name }),
    ],
  });
}

export const TableOfContents = atom('tableOfContents');
export const ChildPages = atom('childPages');
export const Image = atom('image', {
  assetId: data('assetId'),
  src: data('src'),
  alt: data('alt'),
  caption: data('caption'),
  size: data('size'),
  align: data('align'),
});
export const File = atom('file', {
  assetId: data('assetId'),
  name: data('name', ''),
  mimeType: data('mimeType'),
  size: numeric('size'),
});
export const Video = atom('video', {
  assetId: data('assetId'),
  src: data('src'),
  caption: data('caption'),
});

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

export const Mention = inlineAtom('mention', { handle: data('handle', '') }, 'handle');
export const Status = inlineAtom(
  'status',
  { text: data('text', ''), color: data('color', 'grey' satisfies StatusColor) },
  'text',
);
