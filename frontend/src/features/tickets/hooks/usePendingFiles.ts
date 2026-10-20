import { useEffect, useRef, useState } from 'react';
import type { EditorApi } from '../../../components/Markdown/MarkdownEditor';
import { uploadAttachment } from '../../../services/api/attachments';
import { fetchTicket, patchTicket } from '../../../services/api/tickets';
import type { Ticket } from '../../../services/api/types';

export type PendingFile = { id: number; file: File; url: string; placeholder: string };

/**
 * Files pasted or dropped before the ticket exists. Each one leaves a placeholder in the
 * text; once the ticket is created they upload (images at the instance default size)
 * and their placeholders turn into the attachments' markdown.
 */
export function usePendingFiles(editor: React.MutableRefObject<EditorApi | null>) {
  const [files, setFiles] = useState<PendingFile[]>([]);
  const counter = useRef(0);
  const urls = useRef<string[]>([]);
  useEffect(() => () => urls.current.forEach((url) => URL.revokeObjectURL(url)), []);

  const clear = () => {
    for (const f of files) URL.revokeObjectURL(f.url);
    setFiles([]);
  };

  return {
    files,
    add(list: File[]) {
      const added = list.map((file) => {
        const id = (counter.current += 1);
        const url = URL.createObjectURL(file);
        urls.current.push(url);
        const placeholder = `![📎 ${file.name} #${id}]()`;
        editor.current?.insert(placeholder);
        return { id, file, url, placeholder };
      });
      setFiles((current) => [...current, ...added]);
    },
    remove(id: number) {
      const gone = files.find((f) => f.id === id);
      if (!gone) return;
      editor.current?.replace(gone.placeholder, '');
      URL.revokeObjectURL(gone.url);
      setFiles((current) => current.filter((f) => f.id !== id));
    },
    clear,
    /** Uploads the files still in the description and swaps their placeholders. */
    async flush(ticket: Ticket) {
      let text = ticket.description_md;
      const used = files.filter((f) => text.includes(f.placeholder));
      clear();
      if (used.length === 0) return;
      for (const f of used) {
        const attachment = await uploadAttachment(ticket.key, f.file).catch(() => null);
        text = text.replace(f.placeholder, attachment?.markdown ?? '');
      }
      // Uploads can bump the version, so patch on top of the latest one.
      const latest = await fetchTicket(ticket.key);
      await patchTicket(ticket.key, latest.version, { description_md: text });
    },
  };
}
