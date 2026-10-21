import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Input, Select } from '../../../../components/ui/Input';
import type { DbColumn } from '../../../../services/api/folioDatabases';
import { DbValue } from '../DbValue';
import { fromInput } from './value';
import * as S from './style';

type Props = {
  column: DbColumn;
  value: unknown;
  /** Without it the cell only shows the value. */
  onChange?: (value: unknown) => void;
};

const INPUT_TYPE: Partial<Record<DbColumn['type'], string>> = {
  number: 'number',
  date: 'date',
  url: 'url',
};

/** A table cell that edits its value in place: click, change, Enter or leave to save,
 * Escape to cancel. Checkboxes toggle at once; selects save on choosing. */
export function DbCell({ column, value, onChange }: Props) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const label = t('folio.db.edit', { column: column.name });
  if (!onChange) return <DbValue column={column} value={value} />;

  if (column.type === 'checkbox')
    return (
      <input
        type="checkbox"
        aria-label={label}
        checked={!!value}
        onChange={(e) => onChange(e.target.checked)}
      />
    );

  if (!editing)
    return (
      <S.Show
        type="button"
        aria-label={label}
        onClick={() => {
          setDraft(Array.isArray(value) ? '' : value == null ? '' : String(value));
          setEditing(true);
        }}
      >
        <DbValue column={column} value={value} />
      </S.Show>
    );

  const done = (next: unknown) => {
    setEditing(false);
    if (JSON.stringify(next ?? null) !== JSON.stringify(value ?? null)) onChange(next);
  };
  const choices = column.options.choices ?? [];

  if (column.type === 'select')
    return (
      <Select
        aria-label={label}
        autoFocus
        value={draft}
        onChange={(e) => done(e.target.value || null)}
        onBlur={() => setEditing(false)}
      >
        <option value="">{t('folio.db.noValue')}</option>
        {choices.map((c) => (
          <option key={c.value} value={c.value}>
            {c.value}
          </option>
        ))}
      </Select>
    );

  if (column.type === 'multi_select') {
    const picked = Array.isArray(value) ? (value as string[]) : [];
    return (
      <S.Choices role="group" aria-label={label}>
        {choices.map((c) => (
          <label key={c.value}>
            <input
              type="checkbox"
              checked={picked.includes(c.value)}
              onChange={(e) =>
                onChange(
                  e.target.checked ? [...picked, c.value] : picked.filter((v) => v !== c.value),
                )
              }
            />
            {c.value}
          </label>
        ))}
        <button type="button" onClick={() => setEditing(false)}>
          {t('folio.db.done')}
        </button>
      </S.Choices>
    );
  }

  return (
    <Input
      aria-label={label}
      autoFocus
      type={INPUT_TYPE[column.type] ?? 'text'}
      value={draft}
      placeholder={column.type === 'person' ? t('folio.db.personHint') : undefined}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => done(fromInput(column, draft))}
      onKeyDown={(e) => {
        if (e.key === 'Enter') done(fromInput(column, draft));
        if (e.key === 'Escape') setEditing(false);
      }}
    />
  );
}
