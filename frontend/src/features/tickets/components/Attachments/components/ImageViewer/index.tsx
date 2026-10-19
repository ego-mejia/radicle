import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { IconButton } from '../../../../../../components/ui/Button';
import { Modal } from '../../../../../../components/ui/Modal';
import { formatBytes } from '../../../../../../lib/format';
import type { Attachment } from '../../../../../../services/api/types';
import * as S from './style';

type Props = { images: Attachment[]; start: Attachment; onClose: () => void };

/** Large preview of an image attachment; arrows move between the ticket's images. */
export function ImageViewer({ images, start, onClose }: Props) {
  const { t } = useTranslation();
  const [index, setIndex] = useState(
    Math.max(
      0,
      images.findIndex((a) => a.id === start.id),
    ),
  );
  const image = images[index] ?? start;
  const step = (delta: number) =>
    setIndex((i) => (images.length ? (i + delta + images.length) % images.length : 0));
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') step(1);
      if (e.key === 'ArrowLeft') step(-1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });
  return (
    <Modal open onOpenChange={(open) => !open && onClose()} title={image.filename} width={980}>
      <S.Stage>
        {images.length > 1 && (
          <IconButton label={t('attachments.previous')} onClick={() => step(-1)}>
            <ChevronLeft />
          </IconButton>
        )}
        <a href={image.url} target="_blank" rel="noreferrer">
          <img src={image.preview_url ?? image.url} alt={image.filename} />
        </a>
        {images.length > 1 && (
          <IconButton label={t('attachments.next')} onClick={() => step(1)}>
            <ChevronRight />
          </IconButton>
        )}
      </S.Stage>
      <S.Caption>
        {image.width}×{image.height} · {formatBytes(image.size_bytes)} · @{image.uploader.handle}
      </S.Caption>
    </Modal>
  );
}
