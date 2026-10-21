import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { SettingsCard } from '../../../../components/ui/SettingsCard';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  fetchNotificationPreferences,
  notificationKeys,
  setNotificationPreference,
  type NotificationChannel,
  type NotificationPreference,
} from '../../../../services/api/notifications';
import * as S from './style';

/** Profile card: for each kind of notification, whether it reaches you in the app and by email. */
export function NotificationPreferences() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const { data } = useQuery({
    queryKey: notificationKeys.preferences,
    queryFn: fetchNotificationPreferences,
  });
  const save = useMutation({
    mutationFn: setNotificationPreference,
    onSuccess: (prefs) => queryClient.setQueryData(notificationKeys.preferences, prefs),
    onError: (error) => toast(errorMessage(error), 'error'),
  });
  if (!data) return null;

  const toggle = (p: NotificationPreference, channel: NotificationChannel, enabled: boolean) =>
    save.mutate({ app: p.app, type: p.type, channel, enabled });

  return (
    <SettingsCard title={t('notifications.preferences')} help={t('notifications.preferencesHelp')}>
      {data.items.length === 0 ? (
        <S.Muted>{t('notifications.noTypes')}</S.Muted>
      ) : (
        <S.Table>
          <thead>
            <tr>
              <th scope="col">{t('notifications.type')}</th>
              <th scope="col">{t('notifications.inApp')}</th>
              <th scope="col">{t('notifications.email')}</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((p) => (
              <tr key={`${p.app}.${p.type}`}>
                <th scope="row">{p.label}</th>
                <td>
                  <input
                    type="checkbox"
                    aria-label={t('notifications.inAppFor', { label: p.label })}
                    checked={p.in_app}
                    onChange={(e) => toggle(p, 'in_app', e.target.checked)}
                  />
                </td>
                <td>
                  <input
                    type="checkbox"
                    aria-label={t('notifications.emailFor', { label: p.label })}
                    checked={data.email_available && p.email}
                    disabled={!data.email_available}
                    onChange={(e) => toggle(p, 'email', e.target.checked)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </S.Table>
      )}
      {!data.email_available && <S.Muted>{t('notifications.emailOff')}</S.Muted>}
    </SettingsCard>
  );
}
