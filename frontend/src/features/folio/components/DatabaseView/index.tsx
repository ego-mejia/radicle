import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Lock } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { Tabs } from '../../../../components/ui/Tabs';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { isApiError } from '../../../../services/api/client';
import {
  type DbRow,
  type DbRows,
  dbKeys,
  fetchDatabase,
  fetchRows,
  patchRow,
} from '../../../../services/api/folioDatabases';
import { BoardView } from './components/BoardView';
import { CardsView } from './components/CardsView';
import { TableView } from './components/TableView';
import { shown } from './shown';
import * as S from './style';

type Props = {
  nodeId: string;
  /** The view to open; the first one by default. */
  viewId?: string | null;
  /** Inside a page: one view, no views bar. */
  embedded?: boolean;
};

/** A database's rows as one of its views shows them: a table, cards or a board. */
export function DatabaseView({ nodeId, viewId = null, embedded = false }: Props) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const [current, setCurrent] = useState<string | undefined>(viewId ?? undefined);
  const database = useQuery({
    queryKey: dbKeys.database(nodeId),
    queryFn: () => fetchDatabase(nodeId),
    retry: false,
  });
  const rows = useQuery({
    queryKey: dbKeys.rows(nodeId, current),
    queryFn: () => fetchRows(nodeId, current),
    enabled: database.isSuccess,
  });
  const queryClient = useQueryClient();
  const toast = useToast();
  const move = useMutation({
    mutationFn: ({ row, key, value }: { row: DbRow; key: string; value: unknown }) =>
      patchRow(row.id, { values: { [key]: value } }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: dbKeys.database(nodeId) }),
    onError: (e) => toast(errorMessage(e), 'error'),
  });

  if (database.isError) {
    if (isApiError(database.error, 404))
      return (
        <S.NoAccess role="note">
          <Lock aria-hidden />
          {t('folio.db.noAccess')}
        </S.NoAccess>
      );
    return <S.Error role="alert">{errorMessage(database.error)}</S.Error>;
  }
  if (!database.data) return <PageSpinner />;
  const views = database.data.views;
  const active = rows.data?.view.id ?? current ?? views[0]?.id ?? '';

  return (
    <S.Wrap $embedded={embedded}>
      {embedded ? (
        <S.Caption>
          {database.data.title}
          {views.length > 1 && <span> · {views.find((v) => v.id === active)?.name}</span>}
        </S.Caption>
      ) : (
        <Tabs
          label={t('folio.db.views')}
          tabs={views.map((v) => ({ id: v.id, label: v.name }))}
          value={active}
          onChange={setCurrent}
        />
      )}
      {rows.isError && <S.Error role="alert">{errorMessage(rows.error)}</S.Error>}
      {rows.data ? (
        <Shown
          rows={rows.data}
          onMove={
            database.data.can_edit
              ? (row, key, value) => move.mutate({ row, key, value })
              : undefined
          }
        />
      ) : (
        !rows.isError && <PageSpinner />
      )}
    </S.Wrap>
  );
}

type ShownProps = {
  rows: DbRows;
  onMove?: (row: DbRow, key: string, value: unknown) => void;
};

function Shown({ rows, onMove }: ShownProps) {
  const { t } = useTranslation();
  const columns = shown(rows);
  if (rows.view.kind === 'board') {
    const group = rows.columns.find((c) => c.key === rows.view.group_by);
    if (group)
      return (
        <BoardView
          group={group}
          columns={columns}
          rows={rows.items}
          onMove={onMove && ((row, value) => onMove(row, group.key, value))}
        />
      );
  }
  if (rows.items.length === 0) return <S.Empty>{t('folio.db.empty')}</S.Empty>;
  if (rows.view.kind === 'cards') return <CardsView columns={columns} rows={rows.items} />;
  return <TableView columns={columns} rows={rows.items} />;
}
