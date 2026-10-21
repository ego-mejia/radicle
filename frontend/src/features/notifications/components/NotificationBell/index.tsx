import * as Popover from '@radix-ui/react-popover';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from '@tanstack/react-router';
import { Bell } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { relativeTime } from '../../../../lib/format';
import {
  fetchNotifications,
  markRead,
  notificationKeys,
  type Notification,
} from '../../../../services/api/notifications';
import { useNotificationStream } from '../../hooks/useNotificationStream';
import * as S from './style';

/** The bell in both apps' top bars: unread count, the latest notifications, mark read. */
export function NotificationBell() {
  const { t } = useTranslation();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  useNotificationStream();
  const { data } = useQuery({
    queryKey: notificationKeys.list,
    queryFn: () => fetchNotifications(),
    refetchInterval: 60_000,
  });
  const read = useMutation({
    mutationFn: (ids?: string[]) => markRead(ids),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: notificationKeys.list }),
  });
  const unread = data?.unread ?? 0;
  const items = data?.items ?? [];

  const openOne = (n: Notification) => {
    if (!n.read) read.mutate([n.id]);
    setOpen(false);
    if (!n.link) return;
    if (n.link.startsWith('/')) router.history.push(n.link);
    else window.open(n.link, '_blank', 'noopener');
  };

  const label = unread ? t('notifications.bellUnread', { count: unread }) : t('notifications.bell');
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <S.Trigger type="button" aria-label={label} title={label}>
          <Bell aria-hidden />
          {unread > 0 && <S.Count aria-hidden>{unread > 99 ? '99+' : unread}</S.Count>}
        </S.Trigger>
      </Popover.Trigger>
      <Popover.Portal>
        <S.Panel align="end" sideOffset={6} aria-label={t('notifications.title')}>
          <S.Head>
            <h2>{t('notifications.title')}</h2>
            <S.MarkAll type="button" disabled={!unread} onClick={() => read.mutate(undefined)}>
              {t('notifications.markAll')}
            </S.MarkAll>
          </S.Head>
          {items.length === 0 ? (
            <S.Empty>{t('notifications.empty')}</S.Empty>
          ) : (
            <S.List>
              {items.map((n) => (
                <li key={n.id}>
                  <S.Item type="button" $unread={!n.read} onClick={() => openOne(n)}>
                    {!n.read && <S.Dot aria-label={t('notifications.unread')} />}
                    <S.Text>
                      <strong>{n.title}</strong>
                      {n.body && <span>{n.body}</span>}
                      <S.When>{relativeTime(n.created_at)}</S.When>
                    </S.Text>
                  </S.Item>
                </li>
              ))}
            </S.List>
          )}
        </S.Panel>
      </Popover.Portal>
    </Popover.Root>
  );
}
