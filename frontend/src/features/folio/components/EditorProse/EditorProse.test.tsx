import { Editor } from '@tiptap/core';
import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { EVERY_BLOCK } from '../../editor/everyBlock';
import { folioExtensions } from '../../editor/extensions';
import { EditorProse } from '.';

describe('EditorProse', () => {
  it('renders every Folio block with the data attributes it styles', async () => {
    const editor = new Editor({ extensions: folioExtensions(), content: EVERY_BLOCK });
    const html = editor.getHTML();
    editor.destroy();
    renderWithProviders(
      <EditorProse>
        <div data-testid="doc" dangerouslySetInnerHTML={{ __html: html }} />
      </EditorProse>,
    );
    const doc = await screen.findByTestId('doc');
    for (const block of ['panel', 'expand', 'columns', 'tableOfContents', 'image', 'status']) {
      expect(doc.querySelector(`[data-folio="${block}"]`)).not.toBeNull();
    }
    expect(doc.querySelector('[data-folio="panel"]')).toHaveAttribute('data-kind', 'warning');
    expect(doc.querySelector('[data-folio="status"]')).toHaveTextContent('Listo');
  });
});
