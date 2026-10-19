import { useTranslation } from 'react-i18next';
import { appliesTo } from '../../../../../../lib/customFields';
import type { CustomField, Ticket } from '../../../../../../services/api/types';
import { FieldRow, InlineInput, InlineSelect } from '../FieldRow';
import { type Person, PersonSelect } from '../PeopleField';
import * as S from './style';

type Value = string | number | boolean | null;

type Props = {
  ticket: Ticket;
  fields: CustomField[];
  people: Person[];
  canEdit: boolean;
  onChange: (key: string, value: Value) => void;
};

/** Custom fields that apply to the ticket's type and area, editable in place. */
export function CustomFieldRows({ ticket, fields, people, canEdit, onChange }: Props) {
  const { t } = useTranslation();
  const visible = fields.filter((f) => appliesTo(f, ticket));
  if (!visible.length) return null;
  return (
    <>
      <S.Divider />
      {visible.map((field) => (
        <FieldRow key={field.key} label={field.name}>
          <CustomInput
            field={field}
            value={(ticket.custom_fields[field.key] ?? null) as Value}
            people={people}
            disabled={!canEdit}
            emptyLabel={t('fields.noValue')}
            removedLabel={t('fields.removedOption')}
            onChange={(value) => onChange(field.key, value)}
          />
        </FieldRow>
      ))}
    </>
  );
}

type InputProps = {
  field: CustomField;
  value: Value;
  people: Person[];
  disabled: boolean;
  emptyLabel: string;
  removedLabel: string;
  onChange: (value: Value) => void;
};

function CustomInput({
  field,
  value,
  people,
  disabled,
  emptyLabel,
  removedLabel,
  onChange,
}: InputProps) {
  const text = value === null ? '' : String(value);
  switch (field.field_type) {
    case 'select': {
      const known = field.options.some((o) => o.value === value);
      const color = field.options.find((o) => o.value === value)?.color;
      return (
        <S.Picker>
          {color && <S.Dot style={{ background: color }} />}
          <InlineSelect
            label={field.name}
            value={text}
            disabled={disabled}
            onChange={(next) => onChange(next || null)}
            options={[
              { value: '', label: emptyLabel },
              ...(value !== null && !known
                ? [{ value: text, label: `${text} (${removedLabel})` }]
                : []),
              ...field.options.map((o) => ({ value: o.value, label: o.label })),
            ]}
          />
        </S.Picker>
      );
    }
    case 'checkbox':
      return (
        <S.Check
          type="checkbox"
          aria-label={field.name}
          checked={value === true}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
        />
      );
    case 'user':
      return (
        <PersonSelect
          label={field.name}
          people={people}
          value={text}
          disabled={disabled}
          emptyLabel={emptyLabel}
          onChange={(handle) => onChange(handle || null)}
        />
      );
    case 'url':
      return (
        <S.Picker>
          <InlineInput
            label={field.name}
            value={text}
            disabled={disabled}
            placeholder="https://"
            onCommit={(next) => onChange(next.trim() || null)}
          />
          {text && (
            <S.Open href={text} target="_blank" rel="noreferrer noopener">
              ↗
            </S.Open>
          )}
        </S.Picker>
      );
    default:
      return (
        <InlineInput
          label={field.name}
          value={text}
          type={
            field.field_type === 'number' ? 'number' : field.field_type === 'date' ? 'date' : 'text'
          }
          disabled={disabled}
          placeholder="—"
          onCommit={(next) =>
            onChange(next === '' ? null : field.field_type === 'number' ? Number(next) : next)
          }
        />
      );
  }
}
