// Files in the editor: pasted or dropped ones upload to the page and become an image, a
// video or a file block. The `/` menu's Image, File and Video use the same path.

import { Extension, type Editor, type JSONContent } from '@tiptap/core';
import { Plugin } from '@tiptap/pm/state';
import type { FolioAsset } from '../../../services/api/folio';

export type Upload = (file: File) => Promise<FolioAsset>;
type Options = { upload: Upload | null; onError: (error: unknown) => void };

/** The block an uploaded asset becomes. */
export function blockFor(asset: FolioAsset): JSONContent {
  const kind = asset.mime_type.split('/')[0];
  if (kind === 'image') {
    return { type: 'image', attrs: { assetId: asset.id, alt: asset.filename, size: 'large' } };
  }
  if (kind === 'video') return { type: 'video', attrs: { assetId: asset.id } };
  return {
    type: 'file',
    attrs: {
      assetId: asset.id,
      name: asset.filename,
      mimeType: asset.mime_type,
      size: asset.size_bytes,
    },
  };
}

/** Uploads the files one by one and inserts each at `pos` (the cursor by default). */
export async function insertFiles(
  editor: Editor,
  files: File[],
  upload: Upload,
  pos?: number,
): Promise<void> {
  let at = pos;
  for (const file of files) {
    const block = blockFor(await upload(file));
    const chain = editor.chain().focus();
    (at === undefined ? chain.insertContent(block) : chain.insertContentAt(at, block)).run();
    at = undefined; // the next ones follow the cursor, which now sits after this one
  }
}

export const FolioUploads = Extension.create<Options>({
  name: 'folioUploads',
  addOptions: () => ({ upload: null, onError: () => undefined }),
  addProseMirrorPlugins() {
    const { upload, onError } = this.options;
    const editor = this.editor;
    const take = (files: FileList | null | undefined, pos?: number) => {
      const list = Array.from(files ?? []);
      if (!upload || !list.length) return false;
      insertFiles(editor, list, upload, pos).catch(onError);
      return true;
    };
    return [
      new Plugin({
        props: {
          handlePaste: (_view, event) => take(event.clipboardData?.files),
          handleDrop: (view, event) => {
            const at = view.posAtCoords({ left: event.clientX, top: event.clientY });
            return take(event.dataTransfer?.files, at?.pos);
          },
        },
      }),
    ];
  },
});
