import { useQuery } from '@tanstack/react-query';
import { Lock } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { Tabs } from '../../../../components/ui/Tabs';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { isApiError } from '../../../../services/api/client';
import {
  type DbRows,
  dbKeys,
  fetchDatabase,
  fetchRows,
} from '../../../../services/api/folioDatabases';
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

/** A database's rows as one of its views shows them: a table or cards. */
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
      {rows.data ? <Shown rows={rows.data} /> : !rows.isError && <PageSpinner />}
    </S.Wrap>
  );
}

function Shown({ rows }: { rows: DbRows }) {
  const { t } = useTranslation();
  const columns = shown(rows);
  if (rows.items.length === 0) return <S.Empty>{t('folio.db.empty')}</S.Empty>;
  if (rows.view.kind === 'cards') return <CardsView columns={columns} rows={rows.items} />;
  return <TableView columns={columns} rows={rows.items} />;
}
