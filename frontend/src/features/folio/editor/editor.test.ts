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
