import * as Tooltip from '@radix-ui/react-tooltip';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { ticketKeys } from '../../../../services/api/tickets';
import { fetchVoters, setVote, timeKeys } from '../../../../services/api/time';
import type { Ticket } from '../../../../services/api/types';
import * as S from './style';

/** 🙋 with the vote count; hover lists who voted. People vote, agents only read it. */
export function VoteButton({ ticket, canVote }: { ticket: Ticket; canVote: boolean }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [hover, setHover] = useState(false);
  const { data: voters } = useQuery({
    queryKey: [...timeKeys.voters(ticket.key), ticket.vote_count],
    queryFn: () => fetchVoters(ticket.key),
    enabled: hover && ticket.vote_count > 0,
  });
  const toggle = useMutation({
    mutationFn: () => setVote(ticket.key, !ticket.voted_by_me),
    onSuccess: (result) => {
      queryClient.setQueryData<Ticket>(ticketKeys.detail(ticket.key), (old) =>
        old ? { ...old, ...result } : old,
      );
      void queryClient.invalidateQueries({ queryKey: ticketKeys.all, refetchType: 'none' });
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const label = ticket.voted_by_me ? t('votes.remove') : t('votes.add');
  return (
    <Tooltip.Provider delayDuration={300}>
      <Tooltip.Root onOpenChange={setHover}>
        <Tooltip.Trigger asChild>
          <S.Button
            type="button"
            $active={ticket.voted_by_me}
            aria-pressed={ticket.voted_by_me}
            aria-label={`${label} (${ticket.vote_count})`}
            disabled={!canVote || toggle.isPending}
            onClick={() => toggle.mutate()}
          >
            <span aria-hidden>🙋</span>
            {ticket.vote_count}
          </S.Button>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <S.Tip sideOffset={6}>
            {ticket.vote_count === 0
              ? t('votes.none')
              : voters
                ? voters.map((v) => v.display_name).join(', ')
                : t('votes.count', { count: ticket.vote_count })}
          </S.Tip>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}
