import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Avatar } from '../../../../components/ui/Avatar';
import { IconButton } from '../../../../components/ui/Button';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { formatMinutes } from '../../../../lib/duration';
import { formatDateTime } from '../../../../lib/format';
import { ticketKeys } from '../../../../services/api/tickets';
import { deleteWorklog, fetchWorklogs, timeKeys } from '../../../../services/api/time';
import type { Ticket } from '../../../../services/api/types';
import * as S from './style';

type Props = { ticket: Ticket; me: string; isAdmin: boolean; canEdit: boolean };

/** Worklogs of the ticket; people delete their own, admins any. */
export function Worklogs({ ticket, me, isAdmin, canEdit }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const { data, isPending } = useQuery({
    queryKey: [...timeKeys.worklogs(ticket.key), ticket.version],
    queryFn: () => fetchWorklogs(ticket.key),
  });
  const remove = useMutation({
    mutationFn: deleteWorklog,
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticket.key) }),
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  if (isPending) return <PageSpinner />;
  if (!data?.length) return <S.Empty>{t('time.empty')}</S.Empty>;
  return (
    <S.List>
      {data.map((w) => (
        <S.Item key={w.id}>
          <Avatar handle={w.user.handle} name={w.user.display_name} kind={w.user.kind} size={22} />
          <S.Body>
            <strong>{formatMinutes(w.minutes)}</strong>
            <span>{w.description ?? '—'}</span>
            <small>
              @{w.user.handle} · {formatDateTime(w.started_at)}
            </small>
          </S.Body>
          {canEdit && (isAdmin || w.user.handle === me) && (
            <IconButton label={t('time.deleteLog')} onClick={() => remove.mutate(w.id)}>
              <Trash2 />
            </IconButton>
          )}
        </S.Item>
      ))}
    </S.List>
  );
}
