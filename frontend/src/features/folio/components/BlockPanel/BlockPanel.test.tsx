import type { Editor as TipTap, JSONContent } from '@tiptap/core';
import { EditorContent, useEditor } from '@tiptap/react';
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { folioExtensions } from '../../editor/extensions';
import { toFolioDoc } from '../../editor/schema';

let editor: TipTap | null = null;

function Editor({ content }: { content: JSONContent }) {
  editor = useEditor({ extensions: folioExtensions(), content });
  return <EditorContent editor={editor} />;
}

const VISUAL = {
  type: 'visual',
  attrs: { format: 'html', code: '<p>hola</p>', title: 'Saludo', description: '' },
};

describe('the Visual panel', () => {
  it('edits code, title and description with a live preview and the sandbox check', async () => {
    const calls = mockFetch({
      'POST /api/v1/folio/visuals/check': (_req, body) => ({
        status: 200,
        body: {
          valid: !String((body as { code: string }).code).includes('fetch'),
          problems: String((body as { code: string }).code).includes('fetch')
            ? ['fetch() needs the network, which the sandbox blocks.']
            : [],
          warnings: [],
        },
      }),
    });
    renderWithProviders(<Editor content={{ type: 'doc', content: [VISUAL] }} />);
    // A visual without a description opens its panel.
    const panel = await screen.findByRole('complementary', { name: 'Visual (SVG or HTML)' });
    fireEvent.change(within(panel).getByLabelText('Description'), {
      target: { value: 'Un saludo en el color del texto' },
    });
    await waitFor(() =>
      expect(toFolioDoc(editor!.getJSON()).content?.[0]?.attrs?.description).toBe(
        'Un saludo en el color del texto',
      ),
    );
    expect(within(panel).getByText('0.0 KB of 512 KB')).toBeInTheDocument();

    fireEvent.change(within(panel).getByLabelText('Code'), {
      target: { value: "<script>fetch('/x')</script>" },
    });
    expect(await within(panel).findByText(/needs the network/)).toBeInTheDocument();
    expect(calls.at(-1)?.body).toMatchObject({ format: 'html', title: 'Saludo' });

    // The preview switches mode without touching the page's theme.
    const dark = within(panel).getByRole('button', { name: 'Dark' });
    fireEvent.click(dark);
    expect(dark).toHaveAttribute('aria-pressed', 'true');
    const frame = within(panel).getByTitle('Saludo');
    expect(frame.getAttribute('srcdoc')).toContain("fetch('/x')");

    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.queryByRole('complementary')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Edit' }));
    expect(screen.getByRole('complementary')).toBeInTheDocument();
  });
});
