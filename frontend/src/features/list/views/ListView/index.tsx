import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { TicketTable } from '../../../../components/TicketTable';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { currentOrder, withOrder } from '../../../../lib/rqlAssist';
import { isApiError } from '../../../../services/api/client';
import { fetchSearchFields, projectKeys } from '../../../../services/api/projects';
import { ProjectHeader } from '../../../projects/components/ProjectHeader';
import { useProject } from '../../../projects/hooks/useProject';
import { TicketPanel } from '../../../tickets/components/TicketPanel';
import { ticketKeys } from '../../../../services/api/tickets';
import { BulkBar } from '../../components/BulkBar';
import { RqlBar } from '../../components/RqlBar';
import { useTicketSearch } from '../../hooks/useTicketSearch';

export function ListView() {
  const { t } = useTranslation();
  const { key } = useParams({ from: '/app/p/$key/list' });
  const { q, t: openKey } = useSearch({ from: '/app/p/$key/list' });
  const navigate = useNavigate({ from: '/p/$key/list' });
  const projectKey = key.toUpperCase();
  const query = q ?? `project = ${projectKey} AND category != done ORDER BY updated DESC`;
  const { data: project, isPending } = useProject(projectKey);
  const { data: fields } = useQuery({
    queryKey: projectKeys.fields(projectKey),
    queryFn: () => fetchSearchFields(projectKey),
  });
  const search = useTicketSearch(query);
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const select = useCallback((keys: string[], on: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      for (const k of keys) {
        if (on) next.add(k);
        else next.delete(k);
      }
      return next;
    });
  }, []);
  const { fetchNextPage, hasNextPage, isFetchingNextPage } = search;
  const loadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) void fetchNextPage();
  }, [fetchNextPage, hasNextPage, isFetchingNextPage]);

  if (isPending) return <PageSpinner />;
  if (!project) return <EmptyState plant="seed" title={t('board.notFound')} />;

  const error =
    isApiError(search.error, 422) && search.error.problem.position !== undefined
      ? { message: search.error.message, position: search.error.problem.position }
      : null;
  const setQuery = (next: string) => void navigate({ search: { q: next, t: undefined } });

  return (
    <>
      <ProjectHeader project={project} />
      <RqlBar
        value={query}
        onSubmit={setQuery}
        fields={fields}
        error={error}
        warnings={search.warnings.map((w) => w.message)}
      />
      {project.role !== 'viewer' && (
        <BulkBar
          project={project}
          keys={[...selected]}
          onClear={() => setSelected(new Set())}
          onDone={() => {
            setSelected(new Set());
            void queryClient.invalidateQueries({ queryKey: ticketKeys.all });
          }}
        />
      )}
      {search.isPending ? (
        <PageSpinner />
      ) : error ? null : search.items.length === 0 ? (
        <EmptyState plant="pot" title={t('list.emptyTitle')} text={t('list.emptyText')} />
      ) : (
        <TicketTable
          tickets={search.items}
          total={search.total}
          sort={currentOrder(query)}
          onSort={(field) => setQuery(withOrder(query, field))}
          onOpen={(ticketKey) => void navigate({ search: { q, t: ticketKey } })}
          hasMore={!!hasNextPage}
          loadingMore={isFetchingNextPage}
          onLoadMore={loadMore}
          selected={project.role !== 'viewer' ? selected : undefined}
          onSelect={select}
        />
      )}
      <TicketPanel
        ticketKey={openKey}
        onClose={() => void navigate({ search: { q, t: undefined } })}
      />
    </>
  );
}
