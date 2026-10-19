import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { authKeys, setup } from '../../../../services/api/auth';
import { ApiError } from '../../../../services/api/client';
import * as S from '../style';

/** First run: create the instance admin. */
export function SetupView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [form, setForm] = useState({ display_name: '', handle: '', email: '', password: '' });
  const mutation = useMutation({
    mutationFn: setup,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: authKeys.setup });
      await queryClient.invalidateQueries({ queryKey: authKeys.me });
      await navigate({ to: '/' });
    },
  });
  const fieldError = (name: string) =>
    mutation.error instanceof ApiError
      ? mutation.error.problem.errors.find((e) => e.field === name)?.message
      : undefined;
  const set = (name: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [name]: e.target.value });

  return (
    <S.Form
      onSubmit={(e) => {
        e.preventDefault();
        mutation.mutate(form);
      }}
    >
      <S.Heading>
        <h1>{t('auth.setupTitle')}</h1>
        <p>{t('auth.setupText')}</p>
      </S.Heading>
      <FormError>
        {mutation.error && !fieldError('handle') ? errorMessage(mutation.error) : null}
      </FormError>
      <Field label={t('auth.displayName')}>
        <Input value={form.display_name} onChange={set('display_name')} required autoFocus />
      </Field>
      <Field label={t('auth.handle')} hint={t('auth.handleHint')} error={fieldError('handle')}>
        <Input
          value={form.handle}
          onChange={(e) => setForm({ ...form, handle: e.target.value.toLowerCase() })}
          required
          pattern="[a-z0-9][a-z0-9_\-]{1,31}"
        />
      </Field>
      <Field label={t('auth.email')}>
        <Input
          type="email"
          value={form.email}
          onChange={set('email')}
          required
          autoComplete="email"
        />
      </Field>
      <Field label={t('auth.password')} hint={t('auth.passwordHint')}>
        <Input
          type="password"
          value={form.password}
          onChange={set('password')}
          required
          minLength={8}
          autoComplete="new-password"
        />
      </Field>
      <Button type="submit" variant="primary" block disabled={mutation.isPending}>
        {mutation.isPending ? t('common.saving') : t('auth.createAdmin')}
      </Button>
    </S.Form>
  );
}
