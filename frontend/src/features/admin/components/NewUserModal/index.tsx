import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import * as S from './style';

export type NewPerson = { handle: string; display_name: string; email: string; password: string };

type Props = {
  kind: 'human' | 'agent';
  onClose: () => void;
  onCreate: (person: NewPerson) => Promise<unknown>;
};

/** New human (email and temporary password) or agent (handle and name only). */
export function NewUserModal({ kind, onClose, onCreate }: Props) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const [form, setForm] = useState<NewPerson>({
    handle: '',
    display_name: '',
    email: '',
    password: '',
  });
  const mutation = useMutation({ mutationFn: () => onCreate(form), onSuccess: onClose });
  const human = kind === 'human';
  const set = (name: keyof NewPerson) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [name]: name === 'handle' ? e.target.value.toLowerCase() : e.target.value });

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={human ? t('admin.newUser') : t('admin.newAgent')}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button variant="primary" type="submit" form="new-person" disabled={mutation.isPending}>
            {t('common.create')}
          </Button>
        </>
      }
    >
      <S.Form
        id="new-person"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <FormError>{mutation.error ? errorMessage(mutation.error) : null}</FormError>
        <Field label={t('auth.displayName')}>
          <Input value={form.display_name} onChange={set('display_name')} required autoFocus />
        </Field>
        <Field label={t('auth.handle')} hint={t('auth.handleHint')}>
          <Input
            value={form.handle}
            onChange={set('handle')}
            required
            placeholder={human ? 'ana' : 'agent-backend'}
          />
        </Field>
        {human && (
          <>
            <Field label={t('auth.email')}>
              <Input type="email" value={form.email} onChange={set('email')} required />
            </Field>
            <Field label={t('admin.tempPassword')} hint={t('auth.passwordHint')}>
              <Input value={form.password} onChange={set('password')} required minLength={8} />
            </Field>
          </>
        )}
      </S.Form>
    </Modal>
  );
}
