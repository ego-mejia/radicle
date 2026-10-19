import { Lock } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { Tabs } from '../../../../components/ui/Tabs';
import { useMe } from '../../../../hooks/useMe';
import { projectOf } from '../../../../lib/format';
import { rememberTicket } from '../../../../lib/ticketCommands';
import { useTicketCommand } from '../../../../hooks/useTicketCommand';
import { useProject } from '../../../projects/hooks/useProject';
import { useTicket, useTicketActions } from '../../hooks/useTicket';
import { Attachments } from '../Attachments';
import { Comments } from '../Comments';
import { Description } from '../Description';
import { FieldsPanel } from '../FieldsPanel';
import { History } from '../History';
import { Links } from '../Links';
import { Subtickets } from '../Subtickets';
import { TicketHeader } from '../TicketHeader';
import { Worklogs } from '../Worklogs';
import { can, type Permission } from '../../../../lib/permissions';
import * as S from './style';

type Tab = 'comments' | 'history' | 'time';

/** Full ticket view; rendered as a page at /t/KEY and in the side panel. */
export function TicketDetail({ ticketKey }: { ticketKey: string }) {
  const { t } = useTranslation();
  const me = useMe();
  const { data: ticket, isPending, isError } = useTicket(ticketKey);
  const { data: project } = useProject(projectOf(ticketKey));
  const actions = useTicketActions(ticket);
  const [tab, setTab] = useState<Tab>('comments');
  const may = (p: Permission) => can(project, p);
  const canAct = may('ticket.edit');
  useTicketCommand(
    'assign-me',
    () => ticket && actions.patch.mutate({ assignee: me.handle }),
    canAct,
  );
  useEffect(() => {
    if (ticket) rememberTicket({ key: ticket.key, title: ticket.title });
  }, [ticket?.key, ticket?.title]); // eslint-disable-line react-hooks/exhaustive-deps

  if (isPending) return <PageSpinner />;
  if (isError || !ticket) return <EmptyState plant="seed" title={t('ticket.notFound')} />;

  const canEdit = may('ticket.edit');
  const mentions = (project?.members ?? []).map((m) => ({
    handle: m.handle,
    name: m.display_name,
  }));

  return (
    <S.Layout data-ticket-detail={ticket.key}>
      <S.Main>
        {actions.conflict && (
          <S.Conflict role="alert">
            {t('ticket.conflict')}
            <Button size="sm" onClick={() => void actions.reload()}>
              {t('ticket.conflictReload')}
            </Button>
          </S.Conflict>
        )}
        {ticket.security_level && (
          <S.Restricted role="note">
            <Lock size={14} aria-hidden />
            {t('security.banner', { level: ticket.security_level })}
          </S.Restricted>
        )}
        <TicketHeader ticket={ticket} actions={actions} can={may} />
        <Description ticket={ticket} actions={actions} canEdit={canEdit} mentions={mentions} />
        <Attachments
          ticket={ticket}
          canEdit={may('attachment.upload')}
          isAdmin={may('attachment.delete_any')}
          me={me.handle}
        />
        <Subtickets ticket={ticket} canEdit={may('ticket.create')} />
        <Links ticket={ticket} actions={actions} canEdit={may('link.manage')} />
        <S.Activity>
          <Tabs
            label={t('ticket.tabs.comments')}
            value={tab}
            onChange={setTab}
            tabs={[
              { id: 'comments', label: t('ticket.tabs.comments'), count: ticket.comments_count },
              { id: 'history', label: t('ticket.tabs.history') },
              { id: 'time', label: t('ticket.tabs.time') },
            ]}
          />
          {tab === 'comments' ? (
            <Comments
              ticket={ticket}
              me={me.handle}
              canComment={may('comment.create')}
              canModerate={may('comment.delete_any')}
              mentions={mentions}
            />
          ) : tab === 'history' ? (
            <History ticket={ticket} />
          ) : (
            <Worklogs
              ticket={ticket}
              me={me.handle}
              isAdmin={may('worklog.edit_any')}
              canEdit={may('worklog.create')}
            />
          )}
        </S.Activity>
      </S.Main>
      <FieldsPanel ticket={ticket} project={project} actions={actions} canEdit={canEdit} />
    </S.Layout>
  );
}
