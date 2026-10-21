// The visual blocks of Folio 3.3 and 3.4 in the editor, with the server's names and
// attributes (schema.py). Each atom shows what the reader shows; its panel edits it.
// Lists (a chart's rows, a timeline's items) travel as JSON in their data attribute.

import { mergeAttributes, Node } from '@tiptap/core';
import { ReactNodeViewRenderer } from '@tiptap/react';
import { SuiteNodeView } from '../components/SuiteNodeView';

const htmlName = (key: string) => `data-${key.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}`;

type Kind = 'text' | 'number' | 'json';

function attr(key: string, kind: Kind = 'text', fallback: unknown = null) {
  return {
    default: fallback,
    parseHTML: (el: HTMLElement) => {
      const raw = el.getAttribute(htmlName(key));
      if (raw === null) return fallback;
      if (kind === 'number') return Number(raw);
      if (kind === 'json') {
        try {
          return JSON.parse(raw) as unknown;
        } catch {
          return fallback;
        }
      }
      return raw;
    },
    renderHTML: (attrs: Record<string, unknown>) => {
      const value = attrs[key];
      if (value === null || value === undefined) return {};
      return { [htmlName(key)]: kind === 'json' ? JSON.stringify(value) : String(value) };
    },
  };
}

function suiteAtom(name: string, attrs: Record<string, ReturnType<typeof attr>>) {
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
    addNodeView: () => ReactNodeViewRenderer(SuiteNodeView),
  });
}

export const Visual = suiteAtom('visual', {
  format: attr('format', 'text', 'svg'),
  code: attr('code', 'text', ''),
  title: attr('title'),
  description: attr('description', 'text', ''),
});
export const Diagram = suiteAtom('diagram', {
  language: attr('language', 'text', 'mermaid'),
  source: attr('source', 'text', ''),
  caption: attr('caption'),
});
export const Chart = suiteAtom('chart', {
  kind: attr('kind', 'text', 'bar'),
  title: attr('title'),
  data: attr('data', 'json'),
  source: attr('source'),
});
export const Timeline = suiteAtom('timeline', { items: attr('items', 'json', []) });
export const Formula = suiteAtom('formula', { latex: attr('latex', 'text', '') });
export const PageList = suiteAtom('pageList', {
  label: attr('label', 'text', ''),
  limit: attr('limit', 'number'),
  space: attr('space'),
  order: attr('order'),
});

export const InlineFormula = Node.create({
  name: 'inlineFormula',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,
  addAttributes: () => ({ latex: attr('latex', 'text', '') }),
  parseHTML: () => [{ tag: 'span[data-folio="inlineFormula"]' }],
  renderHTML: ({ node, HTMLAttributes }) => [
    'span',
    mergeAttributes(HTMLAttributes, { 'data-folio': 'inlineFormula' }),
    `$${String(node.attrs.latex)}$`,
  ],
  renderText: ({ node }) => String(node.attrs.latex),
  addNodeView: () => ReactNodeViewRenderer(SuiteNodeView),
});

export const Comparison = Node.create({
  name: 'comparison',
  group: 'block',
  content: 'comparisonSide{2,3}',
  isolating: true,
  parseHTML: () => [{ tag: 'div[data-folio="comparison"]' }],
  renderHTML: ({ HTMLAttributes }) => [
    'div',
    mergeAttributes(HTMLAttributes, { 'data-folio': 'comparison' }),
    0,
  ],
});

export const ComparisonSide = Node.create({
  name: 'comparisonSide',
  content: 'block+',
  isolating: true,
  addAttributes: () => ({ title: attr('title') }),
  parseHTML: () => [{ tag: 'div[data-folio="comparisonSide"]' }],
  renderHTML: ({ HTMLAttributes }) => [
    'div',
    mergeAttributes(HTMLAttributes, { 'data-folio': 'comparisonSide' }),
    0,
  ],
});

export const VISUAL_NODES = [
  Visual,
  Diagram,
  Chart,
  Timeline,
  Formula,
  PageList,
  InlineFormula,
  Comparison,
  ComparisonSide,
];
