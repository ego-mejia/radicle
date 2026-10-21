import { Editor } from '@tiptap/core';
import { afterEach, describe, expect, it } from 'vitest';
import en from '../../../i18n/locales/en.json';
import es from '../../../i18n/locales/es.json';
import { BLOCKS, findBlocks } from './blocks';
import { folioExtensions } from './extensions';
import { toFolioDoc } from './schema';

let editor: Editor | null = null;
afterEach(() => editor?.destroy());

const labels = (lang: typeof en) => (key: string) =>
  (lang.folio.editor.blocks as Record<string, string>)[key] ?? key;

describe('the / menu blocks', () => {
  it.each(BLOCKS.map((b) => [b.key, b]))('%s inserts a block the server accepts', (_key, item) => {
    // Text turns another block back into text, so it starts from a heading.
    const content = item.key === 'text' ? '<h2>Hola</h2>' : '<p></p>';
    editor = new Editor({ extensions: folioExtensions(), content });
    expect(item.run(editor.chain().focus()).run()).toBe(true);
    const doc = toFolioDoc(editor.getJSON());
    expect(doc.content?.length).toBeGreaterThan(0);
  });

  it('every block has a label in both languages', () => {
    for (const { key } of BLOCKS) {
      expect(labels(en)(key)).not.toBe(key);
      expect(labels(es)(key)).not.toBe(key);
    }
  });

  it('finds blocks by label or keyword, in any language', () => {
    expect(findBlocks(BLOCKS, 'warn', labels(en)).map((b) => b.key)).toEqual(['panel_warning']);
    expect(findBlocks(BLOCKS, 'tabla', labels(es)).map((b) => b.key)).toEqual([
      'table',
      'toc',
      'ticketTable',
    ]);
    expect(findBlocks(BLOCKS, 'col tres', labels(es)).map((b) => b.key)).toEqual(['columns3']);
    expect(findBlocks(BLOCKS, '', labels(en))).toHaveLength(BLOCKS.length);
  });
});

describe('mentions', () => {
  it('turn @handle into a mention once you type the space', () => {
    editor = new Editor({ extensions: folioExtensions(), content: '<p>hola @fernando</p>' });
    const { view } = editor;
    const end = editor.state.doc.content.size - 1;
    view.someProp('handleTextInput', (f) => f(view, end, end, ' ', () => view.state.tr));
    expect(toFolioDoc(editor.getJSON()).content?.[0]).toEqual({
      type: 'paragraph',
      content: [
        { type: 'text', text: 'hola ' },
        { type: 'mention', attrs: { handle: 'fernando' } },
        { type: 'text', text: ' ' },
      ],
    });
  });
});
