// The action item block (Folio 2.4): a checkbox, its text, @person and an optional due
// date, with a stable id so Mis tareas finds it again. Same name and attributes as the
// server's `actionItem`.

import { mergeAttributes, Node } from '@tiptap/core';
import i18n from '../../../i18n';

/** A fresh id, like the server's `ai-<12 hex>`. */
export function newItemId(): string {
  const hex =
    globalThis.crypto?.randomUUID?.().replace(/-/g, '') ?? Math.random().toString(16).slice(2);
  return `ai-${hex.slice(0, 12)}`;
}

/** A text attribute kept in a `data-*` attribute, so it survives HTML (reloads, pastes). */
function text(key: string) {
  return {
    default: null,
    parseHTML: (el: HTMLElement) => el.getAttribute(`data-${key}`),
    renderHTML: (attrs: Record<string, unknown>) =>
      attrs[key] ? { [`data-${key}`]: String(attrs[key]) } : {},
  };
}

function field(type: 'text' | 'date', value: string, label: string, placeholder = '') {
  const input = document.createElement('input');
  input.type = type;
  input.value = value;
  input.placeholder = placeholder;
  input.setAttribute('aria-label', label);
  return input;
}

export const ActionItem = Node.create({
  name: 'actionItem',
  group: 'block',
  content: 'inline*',
  defining: true,
  addAttributes: () => ({
    id: text('id'),
    done: {
      default: false,
      parseHTML: (el: HTMLElement) => el.getAttribute('data-done') === 'true',
      renderHTML: (attrs: Record<string, unknown>) => (attrs.done ? { 'data-done': 'true' } : {}),
    },
    assignee: text('assignee'),
    due: text('due'),
  }),
  parseHTML: () => [{ tag: 'div[data-folio="actionItem"]' }],
  renderHTML: ({ HTMLAttributes }) => [
    'div',
    mergeAttributes(HTMLAttributes, { 'data-folio': 'actionItem' }),
    0,
  ],

  addNodeView() {
    return ({ node, getPos, editor }) => {
      const dom = document.createElement('div');
      dom.dataset.folio = 'actionItem';
      const box = document.createElement('input');
      box.type = 'checkbox';
      box.contentEditable = 'false';
      box.setAttribute('aria-label', i18n.t('folio.editor.actionItem.done'));
      const content = document.createElement('div');
      content.className = 'action-text';
      const meta = document.createElement('span');
      meta.className = 'action-meta';
      meta.contentEditable = 'false';
      const who = field('text', '', i18n.t('folio.editor.actionItem.assignee'), '@persona');
      const when = field('date', '', i18n.t('folio.editor.actionItem.due'));
      meta.append(who, when);
      dom.append(box, content, meta);

      const set = (attrs: Record<string, unknown>) => {
        const pos = typeof getPos === 'function' ? getPos() : undefined;
        if (pos === undefined) return;
        editor.commands.command(({ tr }) => {
          tr.setNodeMarkup(pos, undefined, { ...editor.state.doc.nodeAt(pos)?.attrs, ...attrs });
          return true;
        });
      };
      const show = (attrs: Record<string, unknown>) => {
        box.checked = Boolean(attrs.done);
        dom.dataset.done = String(Boolean(attrs.done));
        if (document.activeElement !== who)
          who.value = attrs.assignee ? `@${String(attrs.assignee)}` : '';
        if (document.activeElement !== when) when.value = attrs.due ? String(attrs.due) : '';
      };
      box.addEventListener('change', () => set({ done: box.checked }));
      who.addEventListener('change', () => {
        const handle = who.value.trim().replace(/^@/, '').toLowerCase();
        set({ assignee: handle || null });
      });
      when.addEventListener('change', () => set({ due: when.value || null }));
      show(node.attrs);
      if (!node.attrs.id) queueMicrotask(() => set({ id: newItemId() }));

      return {
        dom,
        contentDOM: content,
        update: (updated) => {
          if (updated.type.name !== 'actionItem') return false;
          show(updated.attrs);
          return true;
        },
        stopEvent: (event) =>
          meta.contains(event.target as globalThis.Node) || event.target === box,
        ignoreMutation: (mutation) => !content.contains(mutation.target),
      };
    };
  },

  addKeyboardShortcuts() {
    return {
      // Enter starts the next item with its own id; on an empty item it ends the list.
      Enter: () => {
        const { $from, empty } = this.editor.state.selection;
        const parent = $from.parent;
        if (!empty || parent.type.name !== 'actionItem') return false;
        if (parent.content.size === 0) {
          return this.editor.chain().setNode('paragraph').run();
        }
        const after = $from.after();
        return this.editor
          .chain()
          .insertContentAt(after, { type: 'actionItem', attrs: { id: newItemId(), done: false } })
          .setTextSelection(after + 1)
          .run();
      },
    };
  },
});
