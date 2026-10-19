import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../components/ui/Button';
import { Field, FormError } from '../../../../../../components/ui/Field';
import { Input } from '../../../../../../components/ui/Input';
import { Modal } from '../../../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../../../hooks/useErrorMessage';
import { parseDuration } from '../../../../../../lib/duration';
import { ticketKeys } from '../../../../../../services/api/tickets';
import { addWorklog, timeKeys } from '../../../../../../services/api/time';

type Props = { ticketKey: string; onClose: () => void };

function today(): string {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 16);
}

/** Log time: "1h 30m", "1.5h" or minutes, when it started and what was done. */
export function LogTimeModal({ ticketKey, onClose }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [duration, setDuration] = useState('');
  const [started, setStarted] = useState(today());
  const [description, setDescription] = useState('');
  const minutes = parseDuration(duration);
  const save = useMutation({
    mutationFn: () =>
      addWorklog(ticketKey, {
        minutes: minutes!,
        started_at: new Date(started).toISOString(),
        description: description.trim() || null,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticketKey) });
      await queryClient.invalidateQueries({ queryKey: timeKeys.worklogs(ticketKey) });
      onClose();
    },
  });
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={t('time.logTitle', { key: ticketKey })}
      width={440}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            type="submit"
            form="log-time"
            disabled={!minutes || minutes > 1440 || save.isPending}
          >
            {t('time.log')}
          </Button>
        </>
      }
    >
      <form
        id="log-time"
        style={{ display: 'contents' }}
        onSubmit={(e) => {
          e.preventDefault();
          if (minutes) save.mutate();
        }}
      >
        <FormError>{save.error ? errorMessage(save.error) : null}</FormError>
        <Field
          label={t('time.duration')}
          hint={t('time.durationHint')}
          error={duration && !minutes ? t('time.durationInvalid') : null}
        >
          <Input
            value={duration}
            autoFocus
            placeholder="1h 30m"
            onChange={(e) => setDuration(e.target.value)}
          />
        </Field>
        <Field label={t('time.started')}>
          <Input
            type="datetime-local"
            value={started}
            onChange={(e) => setStarted(e.target.value)}
          />
        </Field>
        <Field label={t('time.description')}>
          <Input value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
      </form>
    </Modal>
  );
}
