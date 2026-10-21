import { Plus, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../../../components/ui/Button';
import { Select } from '../../../../../../components/ui/Input';
import type { DbColumn, DbView } from '../../../../../../services/api/folioDatabases';
import * as S from '../../style';
import { FilterRow } from '../FilterRow';

type Props = {
  columns: DbColumn[];
  draft: DbView;
  set: (patch: Partial<DbView>) => void;
};

/** A view's filters (all must hold) and its sort, each a list of rows. */
export function ViewRules({ columns, draft, set }: Props) {
  const { t } = useTranslation();
  return (
    <>
      <S.Section>
        <h3>{t('folio.db.filters')}</h3>
        {draft.filters.map((f, i) => (
          <FilterRow
            key={i}
            columns={columns}
            filter={f}
            onChange={(next) => set({ filters: draft.filters.map((g, j) => (j === i ? next : g)) })}
            onRemove={() => set({ filters: draft.filters.filter((_, j) => j !== i) })}
          />
        ))}
        <Button
          size="sm"
          variant="ghost"
          onClick={() =>
            set({
              filters: [...draft.filters, { column: columns[0]!.key, op: 'eq', value: null }],
            })
          }
        >
          <Plus aria-hidden />
          {t('folio.db.addFilter')}
        </Button>
      </S.Section>

      <S.Section>
        <h3>{t('folio.db.sort')}</h3>
        {draft.sort.map((s, i) => {
          const change = (patch: Partial<typeof s>) =>
            set({ sort: draft.sort.map((g, j) => (j === i ? { ...g, ...patch } : g)) });
          return (
            <S.Line key={i}>
              <Select
                aria-label={t('folio.db.column')}
                value={s.column}
                onChange={(e) => change({ column: e.target.value })}
              >
                {columns.map((c) => (
                  <option key={c.key} value={c.key}>
                    {c.name}
                  </option>
                ))}
              </Select>
              <Select
                aria-label={t('folio.db.direction')}
                value={s.direction}
                onChange={(e) => change({ direction: e.target.value as 'asc' | 'desc' })}
              >
                <option value="asc">{t('folio.db.asc')}</option>
                <option value="desc">{t('folio.db.desc')}</option>
              </Select>
              <IconButton
                label={t('common.remove')}
                onClick={() => set({ sort: draft.sort.filter((_, j) => j !== i) })}
              >
                <X />
              </IconButton>
            </S.Line>
          );
        })}
        <Button
          size="sm"
          variant="ghost"
          onClick={() =>
            set({ sort: [...draft.sort, { column: columns[0]!.key, direction: 'asc' }] })
          }
        >
          <Plus aria-hidden />
          {t('folio.db.addSort')}
        </Button>
      </S.Section>
    </>
  );
}
