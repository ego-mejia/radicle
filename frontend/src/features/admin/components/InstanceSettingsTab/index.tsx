import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { SettingsCard } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import {
  fetchInstanceSettings,
  patchInstanceSettings,
  ssoKeys,
} from '../../../../services/api/sso';
import { AiProviderSettings } from '../AiProviderSettings';
import { AssistantSettings } from '../AssistantSettings';
import * as S from './style';

/** Instance switches: password sign-in on or off, with the way back in. */
export function InstanceSettingsTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data } = useQuery({ queryKey: ssoKeys.settings, queryFn: fetchInstanceSettings });
  const save = useMutation({
    mutationFn: patchInstanceSettings,
    onSuccess: (next) => queryClient.setQueryData(ssoKeys.settings, next),
  });
  if (!data) return <PageSpinner />;
  return (
    <>
      <SettingsCard title={t('instance.title')}>
        <S.Check>
          <input
            type="checkbox"
            checked={data.password_login_enabled}
            onChange={(e) => save.mutate({ password_login_enabled: e.target.checked })}
          />
          {t('instance.passwordLogin')}
        </S.Check>
        <S.Note $warn={!data.password_login_enabled}>
          {t('instance.emergency', { email: data.emergency_admin ?? '—' })}
        </S.Note>
      </SettingsCard>
      <AiProviderSettings />
      <AssistantSettings />
    </>
  );
}
