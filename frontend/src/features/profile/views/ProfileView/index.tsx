import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { SettingsCard, SettingsParts as P } from '../../../../components/ui/SettingsCard';
import type { ThemePreference } from '../../../../contexts/themeMode';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useMe } from '../../../../hooks/useMe';
import { usePreferences } from '../../../../hooks/usePreferences';
import { useThemeMode } from '../../../../hooks/useThemeMode';
import { useToast } from '../../../../hooks/useToast';
import { LANGUAGES } from '../../../../i18n';
import {
  authKeys,
  createMyToken,
  fetchMyTokens,
  revokeMyToken,
  updateMe,
} from '../../../../services/api/auth';
import { TokenList } from '../../../admin/components/TokenList';
import { TokenReveal } from '../../../admin/components/TokenReveal';
import * as S from './style';

export function ProfileView() {
  const { t, i18n } = useTranslation();
  const me = useMe();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const { preference, setPreference } = useThemeMode();
  const { prefs, save: savePrefs } = usePreferences();
  const [name, setName] = useState(me.display_name);
  const [passwords, setPasswords] = useState({ current_password: '', new_password: '' });
  const [tokenName, setTokenName] = useState('');
  const [revealed, setRevealed] = useState<string | null>(null);
  const onError = (e: unknown) => toast(errorMessage(e), 'error');
  const saveName = useMutation({
    mutationFn: () => updateMe({ display_name: name }),
    onSuccess: (updated) => {
      queryClient.setQueryData(authKeys.me, updated);
      toast(t('profile.saved'));
    },
    onError,
  });
  const savePassword = useMutation({
    mutationFn: () => updateMe(passwords),
    onSuccess: () => {
      setPasswords({ current_password: '', new_password: '' });
      toast(t('profile.passwordChanged'));
    },
    onError,
  });
  const tokens = useQuery({ queryKey: ['me', 'tokens'], queryFn: fetchMyTokens });
  const createToken = useMutation({
    mutationFn: () => createMyToken(tokenName),
    onSuccess: (token) => {
      setRevealed(token.token);
      setTokenName('');
      void tokens.refetch();
    },
    onError,
  });
  const revoke = useMutation({
    mutationFn: revokeMyToken,
    onSuccess: () => void tokens.refetch(),
    onError,
  });

  return (
    <>
      <PageTitle title={t('nav.profile')} subtitle={`@${me.handle} · ${me.email ?? ''}`} />
      <S.Stack>
        <SettingsCard title={t('profile.details')}>
          <S.Form
            onSubmit={(e) => {
              e.preventDefault();
              saveName.mutate();
            }}
          >
            <Field label={t('auth.displayName')}>
              <Input value={name} onChange={(e) => setName(e.target.value)} required />
            </Field>
            <Button type="submit" variant="primary" disabled={name === me.display_name}>
              {t('common.save')}
            </Button>
          </S.Form>
        </SettingsCard>

        <SettingsCard title={t('profile.preferences')}>
          <S.Prefs>
            <Field label={t('language.label')}>
              <Select
                value={i18n.resolvedLanguage}
                onChange={(e) => {
                  void i18n.changeLanguage(e.target.value);
                  savePrefs({ language: e.target.value });
                }}
              >
                {LANGUAGES.map((lng) => (
                  <option key={lng} value={lng}>
                    {lng === 'en' ? 'English' : 'Español'}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label={t('theme.label')}>
              <Select
                value={preference}
                onChange={(e) => {
                  setPreference(e.target.value as ThemePreference);
                  savePrefs({ theme: e.target.value });
                }}
              >
                <option value="system">{t('theme.system')}</option>
                <option value="light">{t('theme.light')}</option>
                <option value="dark">{t('theme.dark')}</option>
              </Select>
            </Field>
            <Field label={t('profile.density')}>
              <Select
                value={prefs?.density ?? 'comfortable'}
                onChange={(e) => {
                  document.documentElement.dataset.density = e.target.value;
                  savePrefs({ density: e.target.value });
                }}
              >
                <option value="comfortable">{t('profile.densities.comfortable')}</option>
                <option value="compact">{t('profile.densities.compact')}</option>
              </Select>
            </Field>
            <Field label={t('profile.shortcuts')} hint={t('profile.shortcutsHint')} group>
              <S.Toggle>
                <input
                  type="checkbox"
                  checked={prefs?.shortcuts ?? true}
                  onChange={(e) => savePrefs({ shortcuts: e.target.checked })}
                />
                {t('profile.shortcutsOn')}
              </S.Toggle>
            </Field>
          </S.Prefs>
        </SettingsCard>

        <SettingsCard title={t('profile.password')}>
          <S.Form
            onSubmit={(e) => {
              e.preventDefault();
              savePassword.mutate();
            }}
          >
            <Field label={t('profile.currentPassword')}>
              <Input
                type="password"
                autoComplete="current-password"
                value={passwords.current_password}
                onChange={(e) => setPasswords({ ...passwords, current_password: e.target.value })}
                required
              />
            </Field>
            <Field label={t('profile.newPassword')} hint={t('auth.passwordHint')}>
              <Input
                type="password"
                autoComplete="new-password"
                minLength={8}
                value={passwords.new_password}
                onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })}
                required
              />
            </Field>
            <Button type="submit" variant="primary">
              {t('profile.changePassword')}
            </Button>
          </S.Form>
        </SettingsCard>

        <SettingsCard title={t('profile.tokens')} help={t('profile.tokensHelp')}>
          {revealed && (
            <TokenReveal
              token={revealed}
              mcpUrl={`${window.location.origin}/mcp`}
              onClose={() => setRevealed(null)}
            />
          )}
          <TokenList tokens={tokens.data ?? []} onRevoke={(id) => revoke.mutate(id)} />
          <P.Inline
            onSubmit={(e) => {
              e.preventDefault();
              createToken.mutate();
            }}
          >
            <Field label={t('profile.tokenName')}>
              <Input
                value={tokenName}
                onChange={(e) => setTokenName(e.target.value)}
                placeholder="claude-code laptop"
                required
              />
            </Field>
            <Button type="submit" variant="primary">
              <KeyRound />
              {t('admin.newToken')}
            </Button>
          </P.Inline>
        </SettingsCard>
      </S.Stack>
    </>
  );
}
