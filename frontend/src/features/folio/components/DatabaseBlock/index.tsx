import { useQuery } from '@tanstack/react-query';
import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';
import { Table2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Select } from '../../../../components/ui/Input';
import { folioKeys, queryDocs } from '../../../../services/api/folio';
import { dbKeys, fetchDatabase } from '../../../../services/api/folioDatabases';
import { DatabaseView } from '../DatabaseView';
import * as S from './style';

const DATABASES = 'kind = database ORDER BY title ASC';

/** The databaseView block in the editor: which database and view it shows, and that view
 * as the page's readers will see it. */
export function DatabaseBlock({ node, updateAttributes, selected }: NodeViewProps) {
  const { t } = useTranslation();
  const database = node.attrs.database as string | null;
  const view = node.attrs.view as string | null;
  const options = useQuery({
    queryKey: folioKeys.query(DATABASES),
    queryFn: () => queryDocs(DATABASES, 100),
    enabled: !database || selected,
  });
  const chosen = useQuery({
    queryKey: dbKeys.database(database ?? ''),
    queryFn: () => fetchDatabase(database!),
    enabled: !!database && selected,
    retry: false,
  });

  return (
    <NodeViewWrapper data-folio="database-view" contentEditable={false}>
      {(!database || selected) && (
        <S.Picker>
          <Table2 aria-hidden />
          <Select
            aria-label={t('folio.db.block.database')}
            value={database ?? ''}
            onChange={(e) => updateAttributes({ database: e.target.value || null, view: null })}
          >
            <option value="">{t('folio.db.block.choose')}</option>
            {options.data?.items.map((d) => (
              <option key={d.id} value={d.id}>
                {d.title}
              </option>
            ))}
          </Select>
          {database && chosen.data && (
            <Select
              aria-label={t('folio.db.block.view')}
              value={view ?? ''}
              onChange={(e) => updateAttributes({ view: e.target.value || null })}
            >
              <option value="">{t('folio.db.block.firstView')}</option>
              {chosen.data.views.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </Select>
          )}
          {options.data?.items.length === 0 && <span>{t('folio.db.block.none')}</span>}
          {database && (
            <Button size="sm" variant="ghost" onClick={() => updateAttributes({ database: null })}>
              {t('common.remove')}
            </Button>
          )}
        </S.Picker>
      )}
      {database && (
        <DatabaseView key={`${database}:${view}`} nodeId={database} viewId={view} embedded />
      )}
    </NodeViewWrapper>
  );
}
