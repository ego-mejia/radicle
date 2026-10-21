// Mirror of the server's document schema (backend/radicle/folio/services/schema.py): which
// attributes each node and mark may carry. TipTap adds defaults the server does not know
// (an ordered list's `type`, a link's `rel`), so documents go through `toFolioDoc` first.

import type { JSONContent } from '@tiptap/core';

export const PANEL_KINDS = ['info', 'tip', 'warning', 'error', 'note'] as const;
export const STATUS_COLORS = ['grey', 'blue', 'green', 'yellow', 'red', 'purple'] as const;
export const COLUMN_LAYOUTS = ['two', 'three', 'sidebar_left', 'sidebar_right'] as const;
export const IMAGE_SIZES = ['small', 'medium', 'large', 'full'] as const;
export const ALIGNS = ['left', 'center', 'right'] as const;

export type PanelKind = (typeof PANEL_KINDS)[number];
export type StatusColor = (typeof STATUS_COLORS)[number];
export type ColumnLayout = (typeof COLUMN_LAYOUTS)[number];

const CELL = ['colspan', 'rowspan', 'colwidth', 'background'];

const NODE_ATTRS: Record<string, string[]> = {
  doc: [],
  paragraph: [],
  heading: ['level', 'id'],
  bulletList: [],
  orderedList: ['start'],
  listItem: [],
  taskList: [],
  taskItem: ['checked'],
  actionItem: ['id', 'done', 'assignee', 'due'],
  blockquote: [],
  codeBlock: ['language'],
  horizontalRule: [],
  table: [],
  tableRow: [],
  tableCell: CELL,
  tableHeader: CELL,
  panel: ['kind'],
  expand: ['title'],
  columns: ['layout'],
  column: [],
  tableOfContents: [],
  childPages: [],
  image: ['assetId', 'src', 'alt', 'caption', 'size', 'align'],
  file: ['assetId', 'name', 'mimeType', 'size'],
  video: ['assetId', 'src', 'caption'],
  embed: ['url', 'title', 'provider'],
  databaseView: ['database', 'view'],
  whiteboard: ['whiteboard'],
  visual: ['format', 'code', 'title', 'description'],
  diagram: ['language', 'source', 'caption'],
  chart: ['kind', 'title', 'data', 'source'],
  timeline: ['items'],
  formula: ['latex'],
  inlineFormula: ['latex'],
  comparison: [],
  comparisonSide: ['title'],
  pageList: ['label', 'limit', 'space', 'order'],
  ticketTable: ['rql', 'title', 'limit'],
  text: [],
  hardBreak: [],
  mention: ['handle'],
  status: ['text', 'color'],
  ticket: ['key'],
};

// Links keep only their target: the reader adds rel and target when it renders them.
const MARK_ATTRS: Record<string, string[]> = {
  bold: [],
  italic: [],
  strike: [],
  underline: [],
  code: [],
  link: ['href'],
};

/** Values TipTap always fills in that mean "nothing special". */
function isDefault(node: string, name: string, value: unknown): boolean {
  if (value === null || value === undefined) return true;
  const spans = name === 'colspan' || name === 'rowspan';
  return spans && (node === 'tableCell' || node === 'tableHeader') && value === 1;
}

function pick(node: string, attrs: Record<string, unknown> | undefined, allowed: string[]) {
  const kept: Record<string, unknown> = {};
  for (const name of allowed) {
    const value = attrs?.[name];
    if (!isDefault(node, name, value)) kept[name] = value;
  }
  return Object.keys(kept).length ? kept : undefined;
}

const blank = (value: unknown) => typeof value !== 'string' || !value.trim();

/** What a visual block still needs before the server takes it, or null when it is
 * complete. Until then the editor shows it but doesn't save it. */
export function incomplete(node: JSONContent): string | null {
  const a = node.attrs ?? {};
  switch (node.type) {
    case 'visual':
      return blank(a.code) ? 'code' : blank(a.description) ? 'description' : null;
    case 'diagram':
      return blank(a.source) ? 'source' : null;
    case 'formula':
    case 'inlineFormula':
      return blank(a.latex) ? 'latex' : null;
    case 'chart':
      return a.source === 'table' || (Array.isArray(a.data) && a.data.length > 1) ? null : 'data';
    case 'timeline':
      return Array.isArray(a.items) && a.items.length ? null : 'items';
    case 'pageList':
      return blank(a.label) ? 'label' : null;
    case 'ticketTable':
      return blank(a.rql) ? 'rql' : null;
    default:
      return null;
  }
}

function clean(node: JSONContent): JSONContent | null {
  const type = node.type ?? '';
  if (!(type in NODE_ATTRS)) return null;
  if (type === 'text' && !node.text) return null;
  // A database block is saved once it names its database.
  if (type === 'databaseView' && !node.attrs?.database) return null;
  if (type === 'whiteboard' && !node.attrs?.whiteboard) return null;
  if (incomplete(node)) return null;
  const out: JSONContent = { type };
  const attrs = pick(type, node.attrs, NODE_ATTRS[type] ?? []);
  if (attrs) out.attrs = attrs;
  if (type === 'text') {
    out.text = node.text;
    const marks = (node.marks ?? [])
      .filter((m) => m.type in MARK_ATTRS)
      .map((m) => {
        const markAttrs = pick(m.type, m.attrs, MARK_ATTRS[m.type] ?? []);
        return markAttrs ? { type: m.type, attrs: markAttrs } : { type: m.type };
      });
    if (marks.length) out.marks = marks;
    return out;
  }
  const content = (node.content ?? []).map(clean).filter((c): c is JSONContent => c !== null);
  if (content.length) out.content = content;
  return out;
}

/** The editor's JSON as the server stores it: known nodes, marks and attributes only. */
export function toFolioDoc(doc: JSONContent): JSONContent {
  return clean({ ...doc, type: 'doc' }) ?? { type: 'doc' };
}
