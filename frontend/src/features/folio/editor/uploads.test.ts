import { Editor } from '@tiptap/core';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { FolioAsset } from '../../../services/api/folio';
import { mediaBlocks } from '../components/PageEditor/media';
import { folioExtensions } from './extensions';
import { toFolioDoc } from './schema';
import { blockFor, insertFiles } from './uploads';

vi.mock('../hooks/pickFiles', () => ({
  pickFiles: vi.fn(async () => [new File(['x'], 'demo.mp4', { type: 'video/mp4' })]),
}));

const asset = (id: string, filename: string, mime: string): FolioAsset => ({
  id,
  url: `/api/v1/folio/assets/${id}`,
  filename,
  mime_type: mime,
  size_bytes: 2048,
  width: null,
  height: null,
  created_at: '2026-10-21T10:00:00Z',
});

const upload = vi.fn(async (file: File) =>
  asset(`id-${file.name}`, file.name, file.type || 'application/octet-stream'),
);

let editor: Editor | null = null;
afterEach(() => editor?.destroy());

describe('uploads', () => {
  it('turn images, videos and other files into their blocks', () => {
    expect(blockFor(asset('a', 'diagrama.png', 'image/png'))).toEqual({
      type: 'image',
      attrs: { assetId: 'a', alt: 'diagrama.png', size: 'large' },
    });
    expect(blockFor(asset('v', 'demo.mp4', 'video/mp4'))).toEqual({
      type: 'video',
      attrs: { assetId: 'v' },
    });
    expect(blockFor(asset('f', 'spec.pdf', 'application/pdf'))).toEqual({
      type: 'file',
      attrs: { assetId: 'f', name: 'spec.pdf', mimeType: 'application/pdf', size: 2048 },
    });
  });

  it('insert one block per file, in order, that the server accepts', async () => {
    editor = new Editor({ extensions: folioExtensions(), content: '<p>Hola</p>' });
    const files = [
      new File(['x'], 'a.png', { type: 'image/png' }),
      new File(['y'], 'b.pdf', { type: 'application/pdf' }),
    ];
    await insertFiles(editor, files, upload);
    const types = toFolioDoc(editor.getJSON()).content?.map((n) => n.type);
    expect(types).toEqual(expect.arrayContaining(['image', 'file']));
    expect(types?.indexOf('image')).toBeLessThan(types?.indexOf('file') ?? -1);
    expect(editor.getHTML()).toContain('src="/api/v1/folio/assets/id-a.png"');
  });

  it('the / menu video item picks a file, uploads it and inserts it', async () => {
    editor = new Editor({ extensions: folioExtensions(), content: '<p></p>' });
    const current = editor;
    const video = mediaBlocks(() => current, upload, vi.fn()).find((b) => b.key === 'video');
    video?.run(current.chain()).run();
    await vi.waitFor(() =>
      expect(toFolioDoc(current.getJSON()).content).toContainEqual({
        type: 'video',
        attrs: { assetId: 'id-demo.mp4' },
      }),
    );
  });
});
