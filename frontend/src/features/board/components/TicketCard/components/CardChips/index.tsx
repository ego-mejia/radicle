import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Check, Flag } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { AreaIcon } from '../../../../../../components/icons/AreaIcon';
import { Menu } from '../../../../../../components/ui/Menu';
import { useErrorMessage } from '../../../../../../hooks/useErrorMessage';
import { useToast } from '../../../../../../hooks/useToast';
import { fetchTicket, patchTicket, ticketKeys } from '../../../../../../services/api/tickets';
import { can } from '../../../../../../lib/permissions';
import type { TicketSummary } from '../../../../../../services/api/types';
import { useProject } from '../../../../../projects/hooks/useProject';
import * as S from './style';

type Props = {
  ticket: TicketSummary;
  showArea: boolean;
  showMilestone: boolean;
  /** False on the drag overlay; otherwise chips change things when the user may edit. */
  interactive: boolean;
};

const stop = (e: React.SyntheticEvent) => e.stopPropagation();

/** Area and milestone as small labels, like Jira's; click one to change it. */
export function CardChips({ ticket, showArea, showMilestone, interactive }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const { data: project } = useProject(ticket.key.split('-')[0]!);
  const editable = interactive && Boolean(project) && can(project!, 'ticket.edit');
  const areas = (project?.areas ?? []).filter((a) => !a.archived);
  const area = project?.areas.find((a) => a.name === ticket.area);
  const milestones = (project?.milestones ?? []).filter(
    (m) => m.status === 'open' || m.name === ticket.milestone,
  );
  const change = useMutation({
    mutationFn: async (body: { area?: string; milestone?: string | null }) => {
      const latest = await fetchTicket(ticket.key); // cards carry no version
      return patchTicket(ticket.key, latest.version, body);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ticketKeys.all }),
    onError: (error) => toast(errorMessage(error), 'error'),
  });

  const chip = (title: string, empty: boolean, children: React.ReactNode) =>
    editable ? (
      <S.Chip as="button" type="button" title={title} data-empty={empty || undefined}>
        {children}
      </S.Chip>
    ) : (
      <S.Chip data-empty={empty || undefined}>{children}</S.Chip>
    );
  const areaChip = chip(
    t('card.changeArea'),
    false,
    <>
      <AreaIcon icon={area?.icon} color={area?.color} size={12} />
      <span>{ticket.area}</span>
    </>,
  );
  const milestoneChip = chip(
    t('card.changeMilestone'),
    !ticket.milestone,
    <>
      <Flag />
      <span>{ticket.milestone ?? t('card.addMilestone')}</span>
    </>,
  );
  const showsArea = showArea && Boolean(ticket.area);
  const showsMilestone = showMilestone && (Boolean(ticket.milestone) || editable);
  if (!showsArea && !showsMilestone) return null;

  return (
    // Menus render in a portal, but React still bubbles their events through here: stop
    // them so picking an option neither opens the ticket nor starts a drag.
    <S.Row onClick={stop} onPointerDown={stop} onKeyDown={stop}>
      {showsArea &&
        (editable && areas.length > 0 ? (
          <Menu
            trigger={areaChip}
            items={areas.map((a) => ({
              key: a.name,
              label: a.name,
              icon: <AreaIcon icon={a.icon} color={a.color} />,
              hint: a.name === ticket.area ? <Check /> : undefined,
              onSelect: () => a.name !== ticket.area && change.mutate({ area: a.name }),
            }))}
          />
        ) : (
          areaChip
        ))}
      {showsMilestone &&
        (editable ? (
          <Menu
            trigger={milestoneChip}
            items={[
              ...milestones.map((m) => ({
                key: m.name,
                label: m.name,
                icon: <Flag />,
                hint: m.name === ticket.milestone ? <Check /> : undefined,
                onSelect: () => m.name !== ticket.milestone && change.mutate({ milestone: m.name }),
              })),
              ...(milestones.length ? [{ separator: true as const, key: 'sep' }] : []),
              {
                key: 'none',
                label: t('card.noMilestone'),
                disabled: !ticket.milestone,
                onSelect: () => change.mutate({ milestone: null }),
              },
            ]}
          />
        ) : (
          milestoneChip
        ))}
    </S.Row>
  );
}
