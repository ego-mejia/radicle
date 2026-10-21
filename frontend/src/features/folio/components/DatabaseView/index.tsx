import { useQuery } from '@tanstack/react-query';
import { Lock, Plus, SlidersHorizontal } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { Tabs } from '../../../../components/ui/Tabs';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { isApiError } from '../../../../services/api/client';
import {
  type DbRow,
  type DbView,
  type DbRows,
  dbKeys,
  fetchDatabase,
  fetchRows,
} from '../../../../services/api/folioDatabases';
import { useRowEdits } from '../../hooks/useRowEdits';
import { ViewSettings } from '../ViewSettings';
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
  const edits = useRowEdits(nodeId);
  // The view being changed, or null for a new one; undefined while closed.
  const [settings, setSettings] = useState<DbView | null | undefined>(undefined);

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
  // Rows are edited on the database's page; inside another page they're only read.
  const canEdit = database.data.can_edit && !embedded;

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
      {canEdit && (
        <S.Toolbar>
          <Button size="sm" onClick={() => edits.add.mutate()} disabled={edits.add.isPending}>
            <Plus aria-hidden />
            {t('folio.db.addRow')}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setSettings(views.find((v) => v.id === active) ?? null)}
          >
            <SlidersHorizontal aria-hidden />
            {t('folio.db.editView')}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setSettings(null)}>
            <Plus aria-hidden />
            {t('folio.db.newView')}
          </Button>
        </S.Toolbar>
      )}
      {rows.isError && <S.Error role="alert">{errorMessage(rows.error)}</S.Error>}
      {rows.data ? (
        <Shown
          rows={rows.data}
          onChange={canEdit ? edits.change : undefined}
          onDelete={canEdit ? edits.remove : undefined}
        />
      ) : (
        !rows.isError && <PageSpinner />
      )}
      {settings !== undefined && (
        <ViewSettings
          database={database.data}
          view={settings}
          onClose={(saved) => {
            setSettings(undefined);
            if (saved) setCurrent(saved);
          }}
        />
      )}
    </S.Wrap>
  );
}

type ShownProps = {
  rows: DbRows;
  onChange?: (row: DbRow, key: string, value: unknown) => void;
  onDelete?: (row: DbRow) => void;
};

function Shown({ rows, onChange, onDelete }: ShownProps) {
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
          onMove={onChange && ((row, value) => onChange(row, group.key, value))}
        />
      );
  }
  if (rows.items.length === 0) return <S.Empty>{t('folio.db.empty')}</S.Empty>;
  if (rows.view.kind === 'cards') return <CardsView columns={columns} rows={rows.items} />;
  return <TableView columns={columns} rows={rows.items} onChange={onChange} onDelete={onDelete} />;
}
