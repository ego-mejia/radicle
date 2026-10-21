import type { Editor as TipTap, JSONContent } from '@tiptap/core';
import { EditorContent, useEditor } from '@tiptap/react';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { folioExtensions } from '../../editor/extensions';
import { toFolioDoc } from '../../editor/schema';

let editor: TipTap | null = null;

function Editor({ content }: { content: JSONContent }) {
  editor = useEditor({ extensions: folioExtensions(), content });
  return <EditorContent editor={editor} />;
}

const side = (title?: string): JSONContent => ({
  type: 'comparisonSide',
  ...(title ? { attrs: { title } } : {}),
  content: [{ type: 'paragraph', content: [{ type: 'text', text: 'x' }] }],
});

describe('ComparisonSideView', () => {
  it('edits the heading of each side', async () => {
    const doc = {
      type: 'doc',
      content: [{ type: 'comparison', content: [side('Antes'), side()] }],
    };
    renderWithProviders(<Editor content={doc} />);
    const [before, after] = await screen.findAllByRole('textbox', { name: 'Side heading' });
    expect(before).toHaveValue('Antes');
    fireEvent.change(after!, { target: { value: 'Después' } });
    await waitFor(() => {
      const sides = toFolioDoc(editor!.getJSON()).content?.[0]?.content ?? [];
      expect(sides.map((s) => s.attrs?.title)).toEqual(['Antes', 'Después']);
    });
  });
});
