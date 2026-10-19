import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { Grid3x3, Table2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { Select } from '../../../../components/ui/Input';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { can } from '../../../../lib/permissions';
import {
  approveItem,
  discardItem,
  duplicateItem,
  fetchInbox,
  inboxKeys,
  type InboxParams,
  scoreItem,
} from '../../../../services/api/inbox';
import { ticketKeys, transitionTicket } from '../../../../services/api/tickets';
import {
  CLASSIFICATIONS,
  type Classification,
  type InboxTab,
  type TicketSummary,
} from '../../../../services/api/types';
import { ProjectHeader } from '../../../projects/components/ProjectHeader';
import { useProject } from '../../../projects/hooks/useProject';
import { TicketPanel } from '../../../tickets/components/TicketPanel';
import { type Approval, ApproveDialog } from '../../components/ApproveDialog';
import { ImpactMatrix } from '../../components/ImpactMatrix';
import { InboxTable, type TriageAction } from '../../components/InboxTable';
import { DiscardDialog, DuplicateDialog } from '../../components/TriageDialogs';
import * as S from './style';

const TABS: InboxTab[] = ['new', 'in_review', 'approved', 'discarded'];
type Dialog = { action: 'approve' | 'duplicate' | 'discard'; ticket: TicketSummary };

/** The project's inbox: drafts to review, score, approve or discard. */
export function InboxView() {
  const { t } = useTranslation();
  const { key } = useParams({ from: '/app/p/$key/inbox' });
  const search = useSearch({ from: '/app/p/$key/inbox' });
  const navigate = useNavigate({ from: '/p/$key/inbox' });
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const projectKey = key.toUpperCase();
  const tab = (TABS.includes(search.tab as InboxTab) ? search.tab : 'new') as InboxTab;
  const view = search.view === 'matrix' ? 'matrix' : 'table';
  const params: InboxParams = {
    tab,
    classification: search.classification as Classification | undefined,
    origin: search.origin as InboxParams['origin'],
    sort: (search.sort as InboxParams['sort']) ?? 'votes',
  };
  const { data: project, isPending: loadingProject, isError } = useProject(projectKey);
  const { data } = useQuery({
    queryKey: inboxKeys.list(projectKey, params),
    queryFn: () => fetchInbox(projectKey, params),
  });
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ticketKeys.all });
  const onError = (e: unknown) => toast(errorMessage(e), 'error');
  const score = useMutation({
    // One at a time: each save reads the version the previous one wrote.
    scope: { id: `inbox-score-${projectKey}` },
    mutationFn: (v: { key: string; impact?: number | null; effort?: number | null }) =>
      scoreItem(v.key, { impact: v.impact, effort: v.effort }),
    onSuccess: refresh,
    onError,
  });
  const review = useMutation({
    mutationFn: (k: string) => transitionTicket(k, { to: 'In Review' }),
    onSuccess: refresh,
    onError,
  });
  const close = () => setDialog(null);
  const done = () => {
    close();
    void refresh();
  };
  const approve = useMutation({
    mutationFn: (v: { key: string; value: Approval }) => approveItem(v.key, v.value),
    onSuccess: (ticket) => {
      done();
      toast(t('inbox.approved', { key: ticket.key, type: t(`ticket.types.${ticket.type}`) }));
    },
  });
  const discard = useMutation({
    mutationFn: (v: { key: string; comment: string | null }) => discardItem(v.key, v.comment),
    onSuccess: done,
  });
  const duplicate = useMutation({
    mutationFn: (v: { key: string; original: string }) => duplicateItem(v.key, v.original),
    onSuccess: done,
  });

  if (loadingProject) return <PageSpinner />;
  if (isError || !project) return <EmptyState plant="seed" title={t('board.notFound')} />;
  const canTriage = can(project, 'inbox.triage');
  const go = (next: Record<string, string | undefined>) =>
    void navigate({ search: { ...search, ...next } });
  const onAction = (action: TriageAction, ticket: TicketSummary) => {
    if (action === 'review') review.mutate(ticket.key);
    else setDialog({ action, ticket });
  };

  return (
    <>
      <ProjectHeader project={project} />
      <S.Bar>
        <S.Tabs role="tablist" aria-label={t('inbox.title')}>
          {TABS.map((id) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={tab === id}
              onClick={() => go({ tab: id })}
            >
              {t(`inbox.tabs.${id}`)} <small>{data?.counts[id] ?? 0}</small>
            </button>
          ))}
        </S.Tabs>
        <S.Spacer />
        <Select
          aria-label={t('inbox.classification')}
          value={params.classification ?? ''}
          onChange={(e) => go({ classification: e.target.value || undefined })}
        >
          <option value="">{t('inbox.allClassifications')}</option>
          {CLASSIFICATIONS.map((c) => (
            <option key={c} value={c}>
              {t(`inbox.classifications.${c}`)}
            </option>
          ))}
        </Select>
        <Select
          aria-label={t('inbox.origin')}
          value={params.origin ?? ''}
          onChange={(e) => go({ origin: e.target.value || undefined })}
        >
          <option value="">{t('inbox.allOrigins')}</option>
          <option value="team">{t('inbox.origins.team')}</option>
          <option value="user">{t('inbox.origins.user')}</option>
        </Select>
        <Select
          aria-label={t('inbox.sort')}
          value={params.sort}
          onChange={(e) => go({ sort: e.target.value })}
        >
          {(['votes', 'age', 'score'] as const).map((s) => (
            <option key={s} value={s}>
              {t(`inbox.sorts.${s}`)}
            </option>
          ))}
        </Select>
        <S.Toggle role="group" aria-label={t('inbox.view')}>
          <button
            type="button"
            aria-pressed={view === 'table'}
            onClick={() => go({ view: undefined })}
          >
            <Table2 size={16} />
            {t('inbox.table')}
          </button>
          <button
            type="button"
            aria-pressed={view === 'matrix'}
            onClick={() => go({ view: 'matrix' })}
          >
            <Grid3x3 size={16} />
            {t('inbox.matrix')}
          </button>
        </S.Toggle>
      </S.Bar>
      {!data ? (
        <PageSpinner />
      ) : data.items.length === 0 ? (
        <EmptyState plant="pot" title={t(`inbox.empty.${tab}`)} />
      ) : view === 'matrix' ? (
        <ImpactMatrix
          items={data.items}
          canTriage={canTriage && (tab === 'new' || tab === 'in_review')}
          onScore={(k, impact, effort) => score.mutate({ key: k, impact, effort })}
        />
      ) : (
        <InboxTable
          items={data.items}
          tab={tab}
          canTriage={canTriage}
          onOpen={(k) => go({ t: k })}
          onScore={(k, field, value) => score.mutate({ key: k, [field]: value })}
          onAction={onAction}
        />
      )}
      {dialog?.action === 'approve' && (
        <ApproveDialog
          ticketKey={dialog.ticket.key}
          project={project}
          pending={approve.isPending}
          error={approve.error ? errorMessage(approve.error) : null}
          onCancel={() => {
            approve.reset();
            close();
          }}
          onApprove={(value) => approve.mutate({ key: dialog.ticket.key, value })}
        />
      )}
      {dialog?.action === 'discard' && (
        <DiscardDialog
          ticketKey={dialog.ticket.key}
          pending={discard.isPending}
          error={discard.error ? errorMessage(discard.error) : null}
          onCancel={() => {
            discard.reset();
            close();
          }}
          onDiscard={(comment) => discard.mutate({ key: dialog.ticket.key, comment })}
        />
      )}
      {dialog?.action === 'duplicate' && (
        <DuplicateDialog
          ticketKey={dialog.ticket.key}
          pending={duplicate.isPending}
          error={duplicate.error ? errorMessage(duplicate.error) : null}
          onCancel={() => {
            duplicate.reset();
            close();
          }}
          onDuplicate={(original) => duplicate.mutate({ key: dialog.ticket.key, original })}
        />
      )}
      <TicketPanel ticketKey={search.t} onClose={() => go({ t: undefined })} />
    </>
  );
}
