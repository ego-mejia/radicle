import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Textarea } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';

type Common = { ticketKey: string; pending: boolean; error: string | null; onCancel: () => void };

/** Discard with an optional note for whoever sent it (shown on their tracking page). */
export function DiscardDialog({
  ticketKey,
  pending,
  error,
  onCancel,
  onDiscard,
}: Common & {
  onDiscard: (comment: string | null) => void;
}) {
  const { t } = useTranslation();
  const [comment, setComment] = useState('');
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onCancel()}
      title={t('inbox.discardTitle', { key: ticketKey })}
      footer={
        <>
          <Button onClick={onCancel}>{t('common.cancel')}</Button>
          <Button
            variant="danger"
            disabled={pending}
            onClick={() => onDiscard(comment.trim() || null)}
          >
            {t('inbox.discard')}
          </Button>
        </>
      }
    >
      <Field label={t('inbox.publicComment')} hint={t('inbox.publicCommentHint')}>
        <Textarea
          rows={3}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          maxLength={2000}
        />
      </Field>
      <FormError>{error}</FormError>
    </Modal>
  );
}

/** Duplicate of another ticket: its voters move to the original. */
export function DuplicateDialog({
  ticketKey,
  pending,
  error,
  onCancel,
  onDuplicate,
}: Common & {
  onDuplicate: (original: string) => void;
}) {
  const { t } = useTranslation();
  const [original, setOriginal] = useState('');
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onCancel()}
      title={t('inbox.duplicateTitle', { key: ticketKey })}
      footer={
        <>
          <Button onClick={onCancel}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            disabled={pending || !original.trim()}
            onClick={() => onDuplicate(original.trim().toUpperCase())}
          >
            {t('inbox.markDuplicate')}
          </Button>
        </>
      }
    >
      <Field label={t('inbox.original')} hint={t('inbox.duplicateHint')}>
        <Input
          value={original}
          onChange={(e) => setOriginal(e.target.value)}
          placeholder="PA-12"
          autoFocus
        />
      </Field>
      <FormError>{error}</FormError>
    </Modal>
  );
}
