import type { TFunction } from 'i18next';
import type { Notification } from '../../../../services/api/notifications';

/** The title in the reader's language, from what the server says it is built of; the
 * server's English title when there's no wording for it here. */
export function notificationTitle(
  n: Pick<Notification, 'app' | 'type' | 'title' | 'params'>,
  t: TFunction,
): string {
  const params = n.params ?? {};
  if (!params.page) return n.title;
  const key = ['notifications.titles', n.app, n.type, params.variant].filter(Boolean).join('.');
  return t(key, {
    ...params,
    actor: params.actor ?? t('notifications.someone'),
    defaultValue: n.title,
  });
}
