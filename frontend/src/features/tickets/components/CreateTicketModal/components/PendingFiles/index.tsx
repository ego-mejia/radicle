import { FileText, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { PendingFile } from '../../../../hooks/usePendingFiles';
import * as S from './style';

type Props = { files: PendingFile[]; onRemove: (id: number) => void };

/** Thumbnails of the files pasted into a ticket that is not created yet. */
export function PendingFiles({ files, onRemove }: Props) {
  const { t } = useTranslation();
  if (files.length === 0) return null;
  return (
    <S.Wrap>
      <S.List>
        {files.map((f) => (
          <S.Item key={f.id} title={f.file.name}>
            {f.file.type.startsWith('image/') ? (
              <img src={f.url} alt={f.file.name} />
            ) : (
              <FileText size={20} aria-label={f.file.name} />
            )}
            <S.Remove
              type="button"
              aria-label={t('create.removeFile', { name: f.file.name })}
              onClick={() => onRemove(f.id)}
            >
              <X size={12} />
            </S.Remove>
          </S.Item>
        ))}
      </S.List>
      <S.Hint>{t('create.filesOnCreate', { count: files.length })}</S.Hint>
    </S.Wrap>
  );
}
