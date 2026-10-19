import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { Tabs } from '../../../../components/ui/Tabs';
import { useMe } from '../../../../hooks/useMe';
import { projectOf } from '../../../../lib/format';
import { useProject } from '../../../projects/hooks/useProject';
import { useTicket, useTicketActions } from '../../hooks/useTicket';
import { Comments } from '../Comments';
import { Description } from '../Description';
import { FieldsPanel } from '../FieldsPanel';
import { History } from '../History';
import { Links } from '../Links';
import { Subtickets } from '../Subtickets';
import { TicketHeader } from '../TicketHeader';
import * as S from './style';

type Tab = 'comments' | 'history';

/** Full ticket view; rendered as a page at /t/KEY and in the side panel. */
export function TicketDetail({ ticketKey }: { ticketKey: string }) {
  const { t } = useTranslation();
  const me = useMe();
  const { data: ticket, isPending, isError } = useTicket(ticketKey);
  const { data: project } = useProject(projectOf(ticketKey));
  const actions = useTicketActions(ticket);
  const [tab, setTab] = useState<Tab>('comments');

  if (isPending) return <PageSpinner />;
  if (isError || !ticket) return <EmptyState plant="seed" title={t('ticket.notFound')} />;

  const role = project?.role ?? 'viewer';
  const canEdit = role !== 'viewer' && !project?.archived;
  const isAdmin = role === 'admin';
  const mentions = (project?.members ?? []).map((m) => ({
    handle: m.handle,
    name: m.display_name,
  }));

  return (
    <S.Layout>
      <S.Main>
        {actions.conflict && (
          <S.Conflict role="alert">
            {t('ticket.conflict')}
            <Button size="sm" onClick={() => void actions.reload()}>
              {t('ticket.conflictReload')}
            </Button>
          </S.Conflict>
        )}
        <TicketHeader
          ticket={ticket}
          actions={actions}
          canEdit={canEdit}
          isAdmin={isAdmin && canEdit}
        />
        <Description ticket={ticket} actions={actions} canEdit={canEdit} mentions={mentions} />
        <Subtickets ticket={ticket} canEdit={canEdit} />
        <Links ticket={ticket} actions={actions} canEdit={canEdit} />
        <S.Activity>
          <Tabs
            label={t('ticket.tabs.comments')}
            value={tab}
            onChange={setTab}
            tabs={[
              { id: 'comments', label: t('ticket.tabs.comments'), count: ticket.comments_count },
              { id: 'history', label: t('ticket.tabs.history') },
            ]}
          />
          {tab === 'comments' ? (
            <Comments
              ticket={ticket}
              me={me.handle}
              canComment={canEdit}
              canModerate={isAdmin}
              mentions={mentions}
            />
          ) : (
            <History ticket={ticket} />
          )}
        </S.Activity>
      </S.Main>
      <FieldsPanel ticket={ticket} project={project} actions={actions} canEdit={canEdit} />
    </S.Layout>
  );
}
