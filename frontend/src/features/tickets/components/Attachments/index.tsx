import { useMutation, useQueryClient } from '@tanstack/react-query';
import { FileText, MoreHorizontal, Paperclip } from 'lucide-react';
import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { IconButton } from '../../../../components/ui/Button';
import { Menu } from '../../../../components/ui/Menu';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { formatBytes } from '../../../../lib/format';
import { deleteAttachment, resizeAttachment } from '../../../../services/api/attachments';
import { ticketKeys } from '../../../../services/api/tickets';
import type { Attachment, ImagePreset, Ticket } from '../../../../services/api/types';
import { useUploads } from '../../hooks/useUploads';
import { Section } from '../Section';
import { UploadStatus } from '../UploadStatus';
import { ImageViewer } from './components/ImageViewer';
import * as S from './style';

type Props = { ticket: Ticket; canEdit: boolean; isAdmin: boolean; me: string };

const SHRINK: { preset: ImagePreset; px: number }[] = [
  { preset: 'large', px: 2048 },
  { preset: 'medium', px: 1280 },
  { preset: 'small', px: 800 },
];

/** Thumbnails grid, upload by button or drop, viewer, shrink and delete. */
export function Attachments({ ticket, canEdit, isAdmin, me }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const uploads = useUploads(ticket.key);
  const [viewing, setViewing] = useState<Attachment | null>(null);
  const [dragging, setDragging] = useState(false);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticket.key) });
  const shrink = useMutation({
    mutationFn: (v: { id: string; preset: ImagePreset }) => resizeAttachment(v.id, v.preset),
    onSuccess: (a) => {
      toast(t('attachments.resized', { name: a.filename, size: formatBytes(a.size_bytes) }));
      void refresh();
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const remove = useMutation({
    mutationFn: (id: string) => deleteAttachment(id),
    onSuccess: () => void refresh(),
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const files = ticket.attachments;
  if (!files.length && !canEdit) return null;
  const images = files.filter((a) => a.is_image);

  return (
    <Section
      title={t('attachments.title', { count: files.length })}
      action={
        canEdit && (
          <IconButton label={t('attachments.add')} onClick={() => input.current?.click()}>
            <Paperclip />
          </IconButton>
        )
      }
    >
      <input
        ref={input}
        type="file"
        multiple
        hidden
        aria-label={t('attachments.add')}
        onChange={(e) => {
          uploads.handleFiles(Array.from(e.target.files ?? []));
          e.target.value = '';
        }}
      />
      <S.Drop
        $active={dragging}
        onDragOver={(e) => {
          if (!canEdit) return;
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          if (!canEdit) return;
          e.preventDefault();
          setDragging(false);
          uploads.handleFiles(Array.from(e.dataTransfer.files));
        }}
      >
        {files.length === 0 ? (
          <S.Empty>{t('attachments.empty')}</S.Empty>
        ) : (
          <S.Grid>
            {files.map((a) => (
              <S.Tile key={a.id}>
                <S.Preview
                  type="button"
                  onClick={() => (a.is_image ? setViewing(a) : window.open(a.url, '_blank'))}
                  aria-label={t('attachments.open', { name: a.filename })}
                >
                  {a.is_image ? (
                    <img src={a.thumb_url ?? a.url} alt="" loading="lazy" />
                  ) : (
                    <FileText />
                  )}
                </S.Preview>
                <S.Meta>
                  <span title={a.filename}>{a.filename}</span>
                  <small>
                    {formatBytes(a.size_bytes)}
                    {a.width ? ` · ${a.width}×${a.height}` : ''}
                  </small>
                </S.Meta>
                <Menu
                  align="end"
                  trigger={
                    <IconButton label={t('attachments.actions', { name: a.filename })}>
                      <MoreHorizontal />
                    </IconButton>
                  }
                  items={[
                    {
                      key: 'download',
                      label: t('attachments.download'),
                      onSelect: () => window.open(a.url, '_blank'),
                    },
                    ...(canEdit && a.is_image
                      ? [
                          { key: 'shrink-label', label: t('attachments.shrink') },
                          ...SHRINK.map(({ preset, px }) => ({
                            key: preset,
                            label: t(`attachments.presets.${preset}`),
                            hint: `${px} px`,
                            disabled: Math.max(a.width ?? 0, a.height ?? 0) <= px,
                            onSelect: () => shrink.mutate({ id: a.id, preset }),
                          })),
                        ]
                      : []),
                    ...(canEdit && (isAdmin || a.uploader.handle === me)
                      ? [
                          { separator: true as const, key: 'sep' },
                          {
                            key: 'delete',
                            label: t('common.delete'),
                            danger: true,
                            onSelect: () => remove.mutate(a.id),
                          },
                        ]
                      : []),
                  ]}
                />
              </S.Tile>
            ))}
          </S.Grid>
        )}
      </S.Drop>
      <UploadStatus uploads={uploads} />
      {viewing && <ImageViewer images={images} start={viewing} onClose={() => setViewing(null)} />}
    </Section>
  );
}
