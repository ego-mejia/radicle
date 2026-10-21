import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { IconButton } from '../../../../../../components/ui/Button';
import { Input, Select } from '../../../../../../components/ui/Input';
import {
  type DbColumn,
  type DbFilter,
  FILTER_OPS,
  type FilterOp,
} from '../../../../../../services/api/folioDatabases';
import { fromInput } from '../../../DbCell/value';
import * as S from '../../style';

type Props = {
  columns: DbColumn[];
  filter: DbFilter;
  onChange: (filter: DbFilter) => void;
  onRemove: () => void;
};

const NO_VALUE: FilterOp[] = ['empty', 'not_empty'];

/** One filter: a column, an operator and, unless it asks for emptiness, a value. */
export function FilterRow({ columns, filter, onChange, onRemove }: Props) {
  const { t } = useTranslation();
  const column = columns.find((c) => c.key === filter.column) ?? columns[0]!;
  const choices = column.options.choices ?? [];
  const value = filter.value == null ? '' : String(filter.value);
  return (
    <S.Line>
      <Select
        aria-label={t('folio.db.column')}
        value={column.key}
        onChange={(e) => onChange({ column: e.target.value, op: filter.op, value: null })}
      >
        {columns.map((c) => (
          <option key={c.key} value={c.key}>
            {c.name}
          </option>
        ))}
      </Select>
      <Select
        aria-label={t('folio.db.operator')}
        value={filter.op}
        onChange={(e) => onChange({ ...filter, op: e.target.value as FilterOp })}
      >
        {FILTER_OPS.map((op) => (
          <option key={op} value={op}>
            {t(`folio.db.op.${op}`)}
          </option>
        ))}
      </Select>
      {NO_VALUE.includes(filter.op) ? null : choices.length > 0 ? (
        <Select
          aria-label={t('folio.db.value')}
          value={value}
          onChange={(e) => onChange({ ...filter, value: e.target.value || null })}
        >
          <option value="" />
          {choices.map((c) => (
            <option key={c.value} value={c.value}>
              {c.value}
            </option>
          ))}
        </Select>
      ) : column.type === 'checkbox' ? (
        <Select
          aria-label={t('folio.db.value')}
          value={value}
          onChange={(e) => onChange({ ...filter, value: e.target.value === 'true' })}
        >
          <option value="true">{t('common.yes')}</option>
          <option value="false">{t('common.no')}</option>
        </Select>
      ) : (
        <Input
          aria-label={t('folio.db.value')}
          type={column.type === 'number' ? 'number' : column.type === 'date' ? 'date' : 'text'}
          value={value}
          onChange={(e) => onChange({ ...filter, value: fromInput(column, e.target.value) })}
        />
      )}
      <IconButton label={t('common.remove')} onClick={onRemove}>
        <X />
      </IconButton>
    </S.Line>
  );
}
