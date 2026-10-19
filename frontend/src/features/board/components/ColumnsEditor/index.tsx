import { ArrowDown, ArrowUp, Plus, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../components/ui/Button';
import { Input } from '../../../../components/ui/Input';
import {
  CATEGORIES,
  type BoardStatus,
  type Category,
  type ColumnConf,
} from '../../../../services/api/types';
import * as S from './style';

type Props = {
  columns: ColumnConf[];
  statuses: BoardStatus[];
  onChange: (columns: ColumnConf[]) => void;
};

/** Board columns: name, statuses or whole categories, and an optional WIP limit. */
export function ColumnsEditor({ columns, statuses, onChange }: Props) {
  const { t } = useTranslation();
  const set = (i: number, patch: Partial<ColumnConf>) =>
    onChange(columns.map((c, j) => (j === i ? { ...c, ...patch } : c)));
  const swap = (i: number, j: number) => {
    const next = [...columns];
    [next[i], next[j]] = [next[j]!, next[i]!];
    onChange(next);
  };
  const toggle = <T,>(list: T[] | undefined, value: T) =>
    (list ?? []).includes(value)
      ? (list ?? []).filter((x) => x !== value)
      : [...(list ?? []), value];
  const used = new Set(columns.flatMap((c) => c.status_ids ?? []));
  const usedCategories = new Set(columns.flatMap((c) => c.categories ?? []));
  const unmapped = statuses.filter((s) => !used.has(s.id) && !usedCategories.has(s.category));

  return (
    <S.List>
      {columns.map((column, i) => (
        <S.Column key={i} aria-label={t('board.columnN', { n: i + 1 })}>
          <S.Head>
            <Input
              aria-label={t('board.columnName')}
              value={column.name}
              onChange={(e) => set(i, { name: e.target.value })}
            />
            <Input
              type="number"
              min={1}
              aria-label={t('board.wipLimit')}
              placeholder={t('board.wipLimit')}
              value={column.wip_limit ?? ''}
              onChange={(e) =>
                set(i, { wip_limit: e.target.value ? Number(e.target.value) : null })
              }
            />
            <IconButton label={t('board.moveUp')} disabled={i === 0} onClick={() => swap(i, i - 1)}>
              <ArrowUp />
            </IconButton>
            <IconButton
              label={t('board.moveDown')}
              disabled={i === columns.length - 1}
              onClick={() => swap(i, i + 1)}
            >
              <ArrowDown />
            </IconButton>
            <IconButton
              label={t('board.removeColumn')}
              disabled={columns.length === 1}
              onClick={() => onChange(columns.filter((_, j) => j !== i))}
            >
              <Trash2 />
            </IconButton>
          </S.Head>
          <S.Options role="group" aria-label={t('board.categories')}>
            {CATEGORIES.map((category: Category) => (
              <label key={category}>
                <input
                  type="checkbox"
                  checked={(column.categories ?? []).includes(category)}
                  onChange={() => set(i, { categories: toggle(column.categories, category) })}
                />
                {t('board.allOf', { category: t(`ticket.categories.${category}`) })}
              </label>
            ))}
          </S.Options>
          <S.Options role="group" aria-label={t('board.statuses')}>
            {statuses.map((status) => (
              <label key={status.id}>
                <input
                  type="checkbox"
                  checked={(column.status_ids ?? []).includes(status.id)}
                  onChange={() => set(i, { status_ids: toggle(column.status_ids, status.id) })}
                />
                {status.name} <small>{t(`ticket.types.${status.type}`)}</small>
              </label>
            ))}
          </S.Options>
        </S.Column>
      ))}
      <Button
        size="sm"
        onClick={() =>
          onChange([...columns, { name: t('board.newColumn'), status_ids: [], categories: [] }])
        }
      >
        <Plus />
        {t('board.addColumn')}
      </Button>
      {unmapped.length > 0 && (
        <S.Warning role="status">
          {t('board.unmapped', { names: unmapped.map((s) => s.name).join(', ') })}
        </S.Warning>
      )}
    </S.List>
  );
}
