import { useQuery } from '@tanstack/react-query';
import { Lock, LockOpen } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Menu } from '../../../../components/ui/Menu';
import { fetchLevels, securityKeys } from '../../../../services/api/security';
import type { Ticket } from '../../../../services/api/types';
import type { TicketActions } from '../../hooks/useTicket';
import * as S from './style';

type Props = { ticket: Ticket; actions: TicketActions; canChange: boolean };

/** The lock: who may see the ticket. Changing it needs ticket.set_security. */
export function SecuritySelect({ ticket, actions, canChange }: Props) {
  const { t } = useTranslation();
  const { data: levels = [] } = useQuery({
    queryKey: securityKeys.levels(ticket.project),
    queryFn: () => fetchLevels(ticket.project),
    enabled: canChange,
  });
  const label = ticket.security_level ?? t('security.public');
  const icon = ticket.security_level ? <Lock size={14} /> : <LockOpen size={14} />;
  if (!canChange) {
    return ticket.security_level ? (
      <S.Chip $locked title={t('security.restrictedTo', { level: label })}>
        {icon}
        {label}
      </S.Chip>
    ) : null;
  }
  return (
    <Menu
      align="end"
      trigger={
        <S.Chip
          as="button"
          type="button"
          $locked={Boolean(ticket.security_level)}
          aria-label={t('security.visibility', { level: label })}
        >
          {icon}
          {label}
        </S.Chip>
      }
      items={[
        {
          key: 'public',
          label: t('security.public'),
          icon: <LockOpen />,
          onSelect: () => actions.patch.mutate({ security_level: null }),
        },
        ...levels.map((level) => ({
          key: level.id,
          label: level.name,
          icon: <Lock />,
          onSelect: () => actions.patch.mutate({ security_level: level.name }),
        })),
      ]}
    />
  );
}
