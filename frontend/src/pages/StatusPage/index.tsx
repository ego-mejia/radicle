/**
 * Placeholder home for deliverable 1.1: proves the SPA is served, talks to the API,
 * and that theme and language switching work. Replaced by the real screens in 1.8.
 */
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Logo } from '../../components/Logo';
import type { ThemePreference } from '../../contexts/themeMode';
import { useThemeMode } from '../../hooks/useThemeMode';
import { LANGUAGES } from '../../i18n';
import { fetchHealth, fetchSetupStatus, systemKeys } from '../../services/api/system';
import * as S from './style';

export function StatusPage() {
  const { t, i18n } = useTranslation();
  const { preference, setPreference } = useThemeMode();
  const health = useQuery({ queryKey: systemKeys.health, queryFn: fetchHealth, retry: false });
  const setup = useQuery({
    queryKey: systemKeys.setupStatus,
    queryFn: fetchSetupStatus,
    enabled: health.isSuccess,
  });

  return (
    <S.Page>
      <S.Card>
        <S.Brand>
          <Logo size={40} />
          <div>
            <S.Title>{t('status.title')}</S.Title>
            <S.Tagline>{t('app.tagline')}</S.Tagline>
          </div>
        </S.Brand>

        {health.isPending && <S.StatusLine $tone="muted">{t('status.checking')}</S.StatusLine>}
        {health.isError && <S.StatusLine $tone="error">{t('status.unhealthy')}</S.StatusLine>}
        {health.isSuccess && <S.StatusLine $tone="ok">{t('status.healthy')}</S.StatusLine>}
        {setup.data && (
          <S.StatusLine $tone="muted">
            {setup.data.needs_setup ? t('status.needsSetup') : t('status.ready')}
          </S.StatusLine>
        )}

        <S.Controls>
          <S.Label>
            {t('status.theme')}
            <S.Select
              value={preference}
              onChange={(e) => setPreference(e.target.value as ThemePreference)}
            >
              <option value="system">{t('status.system')}</option>
              <option value="light">{t('status.light')}</option>
              <option value="dark">{t('status.dark')}</option>
            </S.Select>
          </S.Label>
          <S.Label>
            {t('status.language')}
            <S.Select
              value={i18n.resolvedLanguage}
              onChange={(e) => void i18n.changeLanguage(e.target.value)}
            >
              {LANGUAGES.map((lng) => (
                <option key={lng} value={lng}>
                  {lng === 'en' ? 'English' : 'Español'}
                </option>
              ))}
            </S.Select>
          </S.Label>
        </S.Controls>
      </S.Card>
    </S.Page>
  );
}
