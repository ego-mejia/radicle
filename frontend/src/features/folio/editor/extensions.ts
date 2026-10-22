// The editor's extensions: StarterKit, tables and task lists, plus Folio's own blocks.
// Together they accept exactly the server's schema (see schema.ts).

import { DatabaseViewNode } from './databaseView';
import { WhiteboardNode } from './whiteboard';
import { CalendarNode } from './calendar';
import { PluginBlockNode } from './pluginBlocks';
import { Embed } from './embed';
import { TicketLink } from './ticket';
import { VISUAL_NODES } from './visualNodes';
import type { AnyExtension } from '@tiptap/core';
import { TaskItem, TaskList } from '@tiptap/extension-list';
import { TableCell, TableHeader, TableKit } from '@tiptap/extension-table';
import StarterKit from '@tiptap/starter-kit';
import { ActionItem } from './actionItem';
import {
  ChildPages,
  Column,
  Columns,
  Expand,
  File,
  Image,
  Mention,
  Panel,
  Status,
  TableOfContents,
  Video,
} from './nodes';

// Cells may carry a background color, as in Confluence.
const background = {
  background: {
    default: null,
    parseHTML: (el: HTMLElement) => el.getAttribute('data-background'),
    renderHTML: (attrs: Record<string, unknown>) =>
      attrs.background
        ? { 'data-background': attrs.background, style: `background: ${String(attrs.background)}` }
        : {},
  },
};

const Cell = TableCell.extend({
  addAttributes() {
    return { ...this.parent?.(), ...background };
  },
});

const Header = TableHeader.extend({
  addAttributes() {
    return { ...this.parent?.(), ...background };
  },
});

/** With `shared`, Yjs keeps the history (undo is per person), so StarterKit's goes. */
export function folioExtensions({ shared = false } = {}): AnyExtension[] {
  return [
    StarterKit.configure({
      ...(shared ? { undoRedo: false } : {}),
      heading: { levels: [1, 2, 3, 4] },
      link: { openOnClick: false, autolink: true, defaultProtocol: 'https' },
    }),
    TaskList,
    TaskItem.configure({ nested: true }),
    TableKit.configure({ table: { resizable: false }, tableCell: false, tableHeader: false }),
    Cell,
    Header,
    Panel,
    Expand,
    Columns,
    Column,
    TableOfContents,
    ChildPages,
    Image,
    File,
    Video,
    Embed,
    ...VISUAL_NODES,
    DatabaseViewNode,
    WhiteboardNode,
    CalendarNode,
    PluginBlockNode,
    Mention,
    Status,
    TicketLink,
    ActionItem,
  ];
}
