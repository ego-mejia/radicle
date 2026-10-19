import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useSearch } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { authKeys, fetchAuthOptions, login } from '../../../../services/api/auth';
import { ApiError } from '../../../../services/api/client';
import * as S from '../style';

export function LoginView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { next, sso_error: ssoError } = useSearch({ from: '/auth/login' });
  const { data: options } = useQuery({ queryKey: ['auth-options'], queryFn: fetchAuthOptions });
  const [emergency, setEmergency] = useState(false);
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
        : mutation.error.status === 403
          ? mutation.error.message
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
      <FormError>{error ?? ssoError ?? null}</FormError>
      {(options?.providers ?? []).map((p) => (
        <S.Sso key={p.id} href={`${p.login_url}${next ? `?next=${encodeURIComponent(next)}` : ''}`}>
          {t('auth.continueWith', { name: p.name })}
        </S.Sso>
      ))}
      {options && !options.password_login_enabled && !emergency ? (
        <S.Emergency type="button" onClick={() => setEmergency(true)}>
          {t('auth.emergency')}
        </S.Emergency>
      ) : (
        <>
          {(options?.providers.length ?? 0) > 0 && <S.Or>{t('auth.or')}</S.Or>}
          <PasswordFields
            email={email}
            password={password}
            onEmail={setEmail}
            onPassword={setPassword}
            pending={mutation.isPending}
          />
        </>
      )}
    </S.Form>
  );
}

type FieldsProps = {
  email: string;
  password: string;
  onEmail: (v: string) => void;
  onPassword: (v: string) => void;
  pending: boolean;
};

function PasswordFields({ email, password, onEmail, onPassword, pending }: FieldsProps) {
  const { t } = useTranslation();
  return (
    <>
      <Field label={t('auth.email')}>
        <Input
          type="email"
          value={email}
          onChange={(e) => onEmail(e.target.value)}
          required
          autoFocus
          autoComplete="email"
        />
      </Field>
      <Field label={t('auth.password')}>
        <Input
          type="password"
          value={password}
          onChange={(e) => onPassword(e.target.value)}
          required
          autoComplete="current-password"
        />
      </Field>
      <Button type="submit" variant="primary" block disabled={pending}>
        {pending ? t('common.loading') : t('auth.signIn')}
      </Button>
    </>
  );
}
