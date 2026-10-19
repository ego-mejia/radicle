import * as Popover from '@radix-ui/react-popover';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../components/icons/CategoryIcon';
import { Spinner } from '../../../../components/ui/Spinner';
import { fetchTransitions, ticketKeys } from '../../../../services/api/tickets';
import type { Ticket } from '../../../../services/api/types';
import { useTicketCommand } from '../../../../hooks/useTicketCommand';
import type { TicketActions } from '../../hooks/useTicket';
import { TransitionPicker } from '../TransitionPicker';
import * as S from './style';

type Props = { ticket: Ticket; actions: TicketActions; canEdit: boolean };

/** Current status; opens the transitions available from it. */
export function StatusButton({ ticket, actions, canEdit }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  useTicketCommand('move', () => setOpen(true), canEdit);
  const { data: options, isPending } = useQuery({
    queryKey: [...ticketKeys.transitions(ticket.key), ticket.version],
    queryFn: () => fetchTransitions(ticket.key),
    enabled: open,
  });

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild disabled={!canEdit}>
        <S.Trigger $category={ticket.status.category} aria-label={t('ticket.fields.status')}>
          <CategoryIcon category={ticket.status.category} />
          {ticket.status.name}
          {ticket.resolution && (
            <S.Resolution>· {t(`ticket.resolutions.${ticket.resolution}`)}</S.Resolution>
          )}
          {canEdit && <ChevronDown className="chevron" />}
        </S.Trigger>
      </Popover.Trigger>
      <Popover.Portal>
        <S.Content align="start" sideOffset={4}>
          {isPending ? (
            <Spinner />
          ) : (
            <TransitionPicker
              options={options ?? []}
              projectKey={ticket.project}
              ticketType={ticket.type}
              onPick={({ option, resolution, comment, fields, logMinutes }) => {
                setOpen(false);
                actions.transition.mutate({
                  to: option.to_status,
                  resolution,
                  transition: option.name,
                  comment,
                  fields,
                  log_minutes: logMinutes,
                });
              }}
            />
          )}
        </S.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
