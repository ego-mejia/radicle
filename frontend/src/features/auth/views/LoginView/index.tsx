import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useSearch } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { authKeys, login } from '../../../../services/api/auth';
import { ApiError } from '../../../../services/api/client';
import * as S from '../style';

export function LoginView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { next } = useSearch({ from: '/auth/login' });
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const mutation = useMutation({
    mutationFn: () => login(email, password),
    onSuccess: async (me) => {
      queryClient.setQueryData(authKeys.me, me);
      const target = next && next.startsWith('/') && !next.startsWith('//') ? next : '/';
      await navigate({ to: target });
    },
  });

  let error: string | null = null;
  if (mutation.error instanceof ApiError) {
    error =
      mutation.error.status === 429
        ? t('auth.rateLimited', { seconds: mutation.error.problem.retry_after ?? 60 })
        : t('auth.invalid');
  } else if (mutation.error) {
    error = t('common.unknownError');
  }

  return (
    <S.Form
      onSubmit={(e) => {
        e.preventDefault();
        mutation.mutate();
      }}
    >
      <S.Heading>
        <h1>{t('auth.loginTitle')}</h1>
      </S.Heading>
      <FormError>{error}</FormError>
      <Field label={t('auth.email')}>
        <Input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoFocus
          autoComplete="email"
        />
      </Field>
      <Field label={t('auth.password')}>
        <Input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
        />
      </Field>
      <Button type="submit" variant="primary" block disabled={mutation.isPending}>
        {mutation.isPending ? t('common.loading') : t('auth.signIn')}
      </Button>
    </S.Form>
  );
}
