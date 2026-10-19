import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Modal } from '../../../../components/ui/Modal';
import type { ImagePreset } from '../../../../services/api/types';
import type { Uploads } from '../../hooks/useUploads';
import * as S from './style';

const ORDER: ImagePreset[] = ['original', 'large', 'medium', 'small'];

/** Progress bars for running uploads and the size question for pasted images. */
export function UploadStatus({ uploads }: { uploads: Uploads }) {
  const { t } = useTranslation();
  const [preset, setPreset] = useState<ImagePreset>(uploads.defaultPreset);
  const pending = uploads.pendingImages;
  useEffect(() => {
    if (pending) setPreset(uploads.defaultPreset);
  }, [pending, uploads.defaultPreset]);

  return (
    <>
      {uploads.uploads.map((u) => (
        <S.Upload key={u.id} role="status">
          <span>{t('attachments.uploading', { name: u.name })}</span>
          <S.Bar
            role="progressbar"
            aria-label={u.name}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(u.progress * 100)}
          >
            <span style={{ width: `${Math.round(u.progress * 100)}%` }} />
          </S.Bar>
        </S.Upload>
      ))}
      {pending && (
        <Modal
          open
          onOpenChange={(open) => !open && uploads.cancelImages()}
          title={t('attachments.sizeTitle', { count: pending.length })}
          width={420}
          footer={
            <>
              <Button onClick={uploads.cancelImages}>{t('common.cancel')}</Button>
              <Button variant="primary" autoFocus onClick={() => uploads.confirmImages(preset)}>
                {t('attachments.upload')}
              </Button>
            </>
          }
        >
          <S.Presets role="radiogroup" aria-label={t('attachments.size')}>
            {ORDER.map((value) => (
              <label key={value}>
                <input
                  type="radio"
                  name="image-size"
                  checked={preset === value}
                  onChange={() => setPreset(value)}
                />
                <span>
                  <strong>{t(`attachments.presets.${value}`)}</strong>
                  <small>
                    {uploads.presets[value]
                      ? t('attachments.upTo', { px: uploads.presets[value] })
                      : t('attachments.noResize')}
                  </small>
                </span>
              </label>
            ))}
          </S.Presets>
        </Modal>
      )}
    </>
  );
}
