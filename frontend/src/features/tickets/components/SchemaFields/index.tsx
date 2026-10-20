import { useTranslation } from 'react-i18next';
import { Field } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import { type Values, visibleFields } from '../../../../lib/schemaForm';
import type { SchemaField } from '../../../../services/api/types';
import * as S from './style';

type Props = {
  fields: SchemaField[];
  values: Values;
  onChange: (name: string, value: unknown) => void;
  errors?: Record<string, string | undefined>;
  /** Area chosen in the form, to hide custom fields limited to other areas. */
  area?: string | null;
};

/** One input per schema field, chosen by its kind. Required fields are marked. */
export function SchemaFields({ fields, values, onChange, errors = {}, area }: Props) {
  const { t } = useTranslation();
  const label = (f: SchemaField) => {
    const known = f.field.startsWith('cf.') ? f.label : t(`rules.fields.${f.field}`, f.label);
    return f.required ? `${known} *` : known;
  };
  return (
    <S.Grid>
      {visibleFields(fields, area).map((f) => (
        <Field key={f.field} label={label(f)} error={errors[f.field]}>
          <SchemaInput field={f} value={values[f.field]} onChange={(v) => onChange(f.field, v)} />
        </Field>
      ))}
    </S.Grid>
  );
}

type InputProps = {
  field: SchemaField;
  value: unknown;
  onChange: (value: unknown) => void;
  /** Set by <Field> so its label points at the control. */
  id?: string;
  'aria-describedby'?: string;
};

function SchemaInput({ field, value, onChange, ...a11y }: InputProps) {
  const { t } = useTranslation();
  const text = value === undefined || value === null ? '' : String(value);
  const required = field.required || undefined;
  switch (field.kind) {
    case 'enum':
    case 'area':
    case 'milestone':
    case 'user':
    case 'select':
      return (
        <Select
          {...a11y}
          data-tour={field.kind === 'area' ? 'ticket-form.area' : undefined}
          value={text}
          required={required}
          onChange={(e) => onChange(e.target.value || null)}
        >
          {(field.kind !== 'enum' || !field.required) && <option value="">—</option>}
          {(field.options ?? []).map((o) => (
            <option key={o} value={o}>
              {field.kind === 'enum'
                ? t(`ticket.priorities.${o}`, o)
                : field.kind === 'user'
                  ? `@${o}`
                  : o}
            </option>
          ))}
        </Select>
      );
    case 'users':
    case 'tags':
      return (
        <Input
          {...a11y}
          value={Array.isArray(value) ? value.join(', ') : text}
          placeholder={field.kind === 'tags' ? 'backlog, pagos' : 'luis, ana'}
          onChange={(e) =>
            onChange(
              e.target.value
                .split(/[\s,]+/)
                .map((x) => x.replace(/^[@#]/, ''))
                .filter(Boolean),
            )
          }
        />
      );
    case 'checkbox':
      return (
        <S.Check
          {...a11y}
          type="checkbox"
          checked={value === true}
          onChange={(e) => onChange(e.target.checked)}
        />
      );
    case 'date':
      return (
        <Input
          {...a11y}
          type="date"
          value={text}
          required={required}
          onChange={(e) => onChange(e.target.value || null)}
        />
      );
    case 'number':
      return (
        <Input
          {...a11y}
          type="number"
          step="any"
          value={text}
          required={required}
          onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))}
        />
      );
    case 'ticket':
      return (
        <Input
          {...a11y}
          value={text}
          placeholder="PA-1"
          onChange={(e) => onChange(e.target.value.toUpperCase() || null)}
        />
      );
    default:
      return (
        <Input
          {...a11y}
          type={field.kind === 'url' ? 'url' : 'text'}
          value={text}
          required={required}
          onChange={(e) => onChange(e.target.value || null)}
        />
      );
  }
}
