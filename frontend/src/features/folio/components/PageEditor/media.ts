// Image, File and Video in the `/` menu: each opens the file picker, uploads to the page and
// inserts the block where the menu was.

import type { Editor } from '@tiptap/core';
import type { BlockItem } from '../../editor/blocks';
import { insertFiles, type Upload } from '../../editor/uploads';
import { pickFiles } from '../../hooks/pickFiles';

const KINDS = [
  { key: 'image', accept: 'image/*', keywords: 'image picture foto imagen png jpg' },
  { key: 'file', accept: '*/*', keywords: 'file attachment archivo adjunto pdf' },
  { key: 'video', accept: 'video/*', keywords: 'video movie mp4 pelicula' },
];

export function mediaBlocks(
  editor: () => Editor | null,
  upload: Upload,
  onError: (error: unknown) => void,
): BlockItem[] {
  return KINDS.map(({ key, accept, keywords }) => ({
    key,
    keywords,
    run: (chain) => {
      void pickFiles(accept).then((files) => {
        const current = editor();
        if (current && files.length) insertFiles(current, files, upload).catch(onError);
      });
      return chain;
    },
  }));
}
