import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../components/icons/CategoryIcon';
import { TypeIcon } from '../../../../components/icons/TypeIcon';
import { TicketKey } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { useCreateTicket } from '../../../../hooks/useCreateTicket';
import { fetchChildren, ticketKeys } from '../../../../services/api/tickets';
import type { Ticket } from '../../../../services/api/types';
import { Section, SectionParts as S } from '../Section';

export function Subtickets({ ticket, canEdit }: { ticket: Ticket; canEdit: boolean }) {
  const { t } = useTranslation();
  const openCreate = useCreateTicket();
  const { data: children = [] } = useQuery({
    queryKey: [...ticketKeys.children(ticket.key), ticket.children_count],
    queryFn: () => fetchChildren(ticket.key),
    enabled: ticket.children_count > 0,
  });

  return (
    <Section
      title={t('ticket.subtickets')}
      action={
        canEdit && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              openCreate({
                project: ticket.project,
                parent: ticket.key,
                area: ticket.area,
                milestone: ticket.milestone,
              })
            }
          >
            <Plus />
            {t('ticket.createSubticket')}
          </Button>
        )
      }
    >
      {ticket.children_count === 0 ? (
        <S.Muted>{t('ticket.noSubtickets')}</S.Muted>
      ) : (
        children.map((child) => (
          <S.Row key={child.key}>
            <Link to="/t/$key" params={{ key: child.key }}>
              <TypeIcon type={child.type} />
              <TicketKey>{child.key}</TicketKey>
              <span className="title">{child.title}</span>
            </Link>
            <CategoryIcon category={child.status.category} title={child.status.name} />
            <S.GroupLabel>{child.status.name}</S.GroupLabel>
          </S.Row>
        ))
      )}
    </Section>
  );
}
