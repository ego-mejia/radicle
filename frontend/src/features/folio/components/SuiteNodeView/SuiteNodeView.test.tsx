import { EditorContent, useEditor } from '@tiptap/react';
import type { JSONContent } from '@tiptap/core';
import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { folioExtensions } from '../../editor/extensions';

function Editor({ content }: { content: JSONContent }) {
  const editor = useEditor({ extensions: folioExtensions(), content });
  return <EditorContent editor={editor} />;
}

const cell = (type: string, text: string): JSONContent => ({
  type,
  content: [{ type: 'paragraph', content: [{ type: 'text', text }] }],
});

describe('SuiteNodeView', () => {
  it('shows a visual as the reader will, and what an incomplete one still needs', async () => {
    const visual = (description: string): JSONContent => ({
      type: 'visual',
      attrs: { format: 'svg', code: '<svg/>', title: 'Raíz', description },
    });
    renderWithProviders(
      <Editor content={{ type: 'doc', content: [visual('Un círculo'), visual('')] }} />,
    );
    expect((await screen.findAllByTitle('Raíz'))[0]).toHaveAttribute('sandbox', 'allow-scripts');
    expect(screen.getByText(/without a description it isn't saved/)).toBeInTheDocument();
  });

  it('draws a chart from the table right before it', async () => {
    const table: JSONContent = {
      type: 'table',
      content: [
        { type: 'tableRow', content: [cell('tableHeader', 'Área'), cell('tableHeader', 'N')] },
        { type: 'tableRow', content: [cell('tableCell', 'Legal'), cell('tableCell', '3')] },
      ],
    };
    const chart = { type: 'chart', attrs: { kind: 'bar', source: 'table', title: 'Del cuadro' } };
    renderWithProviders(<Editor content={{ type: 'doc', content: [table, chart] }} />);
    expect(await screen.findByRole('img', { name: 'Del cuadro' })).toBeInTheDocument();
  });
});
