import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Settings } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { folioKeys, type FolioSpace } from '../../../../services/api/folio';
import { patchSpace } from '../../../../services/api/folioSocial';

/** Space settings for its admins: how many days a Verified page stays verified. */
export function SpaceSettings({ space }: { space: FolioSpace }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [days, setDays] = useState(String(space.verify_days));
  const [error, setError] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: () => patchSpace(space.key, { verify_days: Number(days) }),
    onSuccess: (updated) => {
      client.setQueryData(folioKeys.space(space.key), updated);
      setOpen(false);
      toast(t('folio.spaceSettings.saved'));
    },
    onError: (e) => setError(errorMessage(e)),
  });

  return (
    <>
      <Button onClick={() => setOpen(true)} aria-label={t('folio.spaceSettings.title')}>
        <Settings aria-hidden />
      </Button>
      <Modal
        open={open}
        onOpenChange={setOpen}
        title={t('folio.spaceSettings.title')}
        footer={
          <>
            <Button onClick={() => setOpen(false)}>{t('common.cancel')}</Button>
            <Button
              variant="primary"
              disabled={save.isPending}
              onClick={() => {
                setError(null);
                save.mutate();
              }}
            >
              {t('common.save')}
            </Button>
          </>
        }
      >
        <Field
          label={t('folio.spaceSettings.verifyDays')}
          hint={t('folio.spaceSettings.verifyDaysHint')}
          error={error}
        >
          <Input
            type="number"
            min={1}
            max={730}
            value={days}
            onChange={(e) => setDays(e.target.value)}
          />
        </Field>
      </Modal>
    </>
  );
}
