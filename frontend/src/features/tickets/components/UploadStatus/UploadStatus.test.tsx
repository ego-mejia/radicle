import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRef } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { EditorApi } from '../../../../components/Markdown/MarkdownEditor';
import i18n from '../../../../i18n';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { useUploads } from '../../hooks/useUploads';
import { UploadStatus } from '.';

const upload = vi.fn();
vi.mock('../../../../services/api/attachments', async (original) => ({
  ...(await original<typeof import('../../../../services/api/attachments')>()),
  fetchLimits: async () => ({
    max_upload_mb: 25,
    image_default_resize: 'medium',
    image_presets: { original: null, large: 2048, medium: 1280, small: 800 },
  }),
  uploadAttachment: (...args: unknown[]) => upload(...args),
}));

const text: string[] = [];
const editorApi: EditorApi = {
  insert: (t) => text.push(t),
  replace: (from, to) => text.splice(text.indexOf(from), 1, to),
};

const noop = () => undefined;
let files: (list: File[]) => void = noop;

function Harness() {
  const editor = useRef<EditorApi | null>(editorApi);
  const uploads = useUploads('PA-1', editor);
  files = uploads.handleFiles;
  return <UploadStatus uploads={uploads} />;
}

describe('pasting an image', () => {
  beforeEach(() => {
    void i18n.changeLanguage('en');
    upload.mockReset();
    text.length = 0;
    files = noop;
  });

  it('asks for the size with the default selected and inserts the markdown', async () => {
    upload.mockResolvedValue({ markdown: '![shot.png](attachment:abc)' });
    renderWithProviders(<Harness />);
    await waitFor(() => expect(files).not.toBe(noop));
    files([new File(['x'], 'shot.png', { type: 'image/png' })]);
    const medium = await screen.findByRole('radio', { name: /Medium/ });
    await waitFor(() => expect(medium).toBeChecked());
    await userEvent.click(screen.getByRole('radio', { name: /Small/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Upload' }));
    await waitFor(() => expect(text).toEqual(['![shot.png](attachment:abc)']));
    expect(upload.mock.calls[0]![2]).toEqual({ resize: 'small' });
  });

  it('uploads other files right away', async () => {
    upload.mockResolvedValue({ markdown: '[notes.txt](attachment:def)' });
    renderWithProviders(<Harness />);
    await waitFor(() => expect(files).not.toBe(noop));
    files([new File(['hola'], 'notes.txt', { type: 'text/plain' })]);
    await waitFor(() => expect(text).toEqual(['[notes.txt](attachment:def)']));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});
