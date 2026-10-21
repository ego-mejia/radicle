import { Editor } from '@tiptap/core';
import { afterEach, describe, expect, it } from 'vitest';
import { EVERY_BLOCK } from './everyBlock';
import { folioExtensions } from './extensions';
import { toFolioDoc } from './schema';

let editor: Editor | null = null;

function load(content: object): Editor {
  editor = new Editor({ extensions: folioExtensions(), content });
  return editor;
}

afterEach(() => {
  editor?.destroy();
  editor = null;
});

describe('the Folio editor schema', () => {
  it('keeps every block of the server schema through a round trip', () => {
    expect(toFolioDoc(load(EVERY_BLOCK).getJSON())).toEqual(EVERY_BLOCK);
  });

  it('survives HTML, as when the editor is reloaded or content is pasted', () => {
    const html = load(EVERY_BLOCK).getHTML();
    editor?.destroy();
    const reloaded = load({ type: 'doc' });
    reloaded.commands.setContent(html);
    expect(toFolioDoc(reloaded.getJSON())).toEqual(EVERY_BLOCK);
  });

  it("drops what the server would reject: TipTap's defaults and unknown nodes", () => {
    const doc = toFolioDoc({
      type: 'doc',
      content: [
        { type: 'orderedList', attrs: { start: 3, type: null }, content: [] },
        {
          type: 'paragraph',
          content: [
            {
              type: 'text',
              text: 'x',
              marks: [{ type: 'link', attrs: { href: '/a', rel: 'nofollow', target: '_blank' } }],
            },
          ],
        },
        { type: 'youtube', attrs: { src: 'x' } },
        { type: 'tableCell', attrs: { colspan: 1, rowspan: 2, colwidth: null } },
      ],
    });
    expect(doc.content).toEqual([
      { type: 'orderedList', attrs: { start: 3 } },
      {
        type: 'paragraph',
        content: [{ type: 'text', text: 'x', marks: [{ type: 'link', attrs: { href: '/a' } }] }],
      },
      { type: 'tableCell', attrs: { rowspan: 2 } },
    ]);
  });
});

describe('the action item block', () => {
  const ITEM = {
    type: 'doc',
    content: [
      {
        type: 'actionItem',
        attrs: { id: 'ai-1', done: true, assignee: 'ana', due: '2026-11-01' },
        content: [{ type: 'text', text: 'Mandar el contrato' }],
      },
      // TipTap keeps a paragraph after a last block like this one.
      { type: 'paragraph', content: [{ type: 'text', text: 'Fin' }] },
    ],
  };

  it('keeps its id, person, date and check through JSON and HTML', () => {
    const first = load(ITEM);
    expect(toFolioDoc(first.getJSON())).toEqual(ITEM);
    const html = first.getHTML();
    first.destroy();
    const reloaded = load({ type: 'doc' });
    reloaded.commands.setContent(html);
    expect(toFolioDoc(reloaded.getJSON())).toEqual(ITEM);
  });

  it('starts the next item with its own id on Enter', () => {
    const e = load(ITEM);
    e.commands.setTextSelection(1 + 'Mandar el contrato'.length); // end of the item
    e.commands.keyboardShortcut('Enter');
    const items = e.getJSON().content ?? [];
    expect(items.map((i) => i.type)).toEqual(['actionItem', 'actionItem', 'paragraph']);
    expect(items[1]?.attrs?.id).toMatch(/^ai-[0-9a-f]{12}$/);
    expect(items[1]?.attrs?.id).not.toBe('ai-1');
  });
});
