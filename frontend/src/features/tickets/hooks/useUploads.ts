import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import type { EditorApi } from '../../../components/Markdown/MarkdownEditor';
import { useErrorMessage } from '../../../hooks/useErrorMessage';
import { useToast } from '../../../hooks/useToast';
import { attachmentKeys, fetchLimits, uploadAttachment } from '../../../services/api/attachments';
import { ticketKeys } from '../../../services/api/tickets';
import type { Attachment, ImagePreset } from '../../../services/api/types';

export type Upload = { id: number; name: string; progress: number };

const IMAGE = /^image\/(png|jpeg|webp|gif)$/;

/**
 * Uploads for one ticket. Pasted or dropped images first ask for a size (the
 * instance default is preselected); other files go straight up. While a file uploads,
 * the editor shows a placeholder that becomes its markdown when it is done.
 */
export function useUploads(ticketKey: string, editor?: React.MutableRefObject<EditorApi | null>) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const { data: limits } = useQuery({ queryKey: attachmentKeys.limits, queryFn: fetchLimits });
  const [uploads, setUploads] = useState<Upload[]>([]);
  const [pendingImages, setPendingImages] = useState<File[] | null>(null);
  const counter = useRef(0);
  const defaultPreset = (limits?.image_default_resize ?? 'large') as ImagePreset;
  const maxBytes = (limits?.max_upload_mb ?? 25) * 1024 * 1024;

  const start = async (file: File, preset?: ImagePreset): Promise<Attachment | null> => {
    if (file.size > maxBytes) {
      toast(`${file.name}: > ${limits?.max_upload_mb ?? 25} MB`, 'error');
      return null;
    }
    const id = (counter.current += 1);
    const placeholder = `![⏳ ${file.name} #${id}]()`;
    editor?.current?.insert(placeholder);
    setUploads((list) => [...list, { id, name: file.name, progress: 0 }]);
    try {
      const attachment = await uploadAttachment(ticketKey, file, { resize: preset }, (p) =>
        setUploads((list) => list.map((u) => (u.id === id ? { ...u, progress: p } : u))),
      );
      editor?.current?.replace(placeholder, attachment.markdown);
      void queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketKey) });
      return attachment;
    } catch (error) {
      editor?.current?.replace(placeholder, '');
      toast(`${file.name}: ${errorMessage(error)}`, 'error');
      return null;
    } finally {
      setUploads((list) => list.filter((u) => u.id !== id));
    }
  };

  return {
    uploads,
    pendingImages,
    defaultPreset,
    presets: limits?.image_presets ?? { original: null, large: 2048, medium: 1280, small: 800 },
    /** Files from paste, drop or a file picker. */
    handleFiles(files: File[]) {
      const images = files.filter((f) => IMAGE.test(f.type));
      for (const file of files.filter((f) => !IMAGE.test(f.type))) void start(file);
      if (images.length) setPendingImages(images);
    },
    confirmImages(preset: ImagePreset) {
      const images = pendingImages ?? [];
      setPendingImages(null);
      for (const file of images) void start(file, preset);
    },
    cancelImages() {
      setPendingImages(null);
    },
  };
}

export type Uploads = ReturnType<typeof useUploads>;
