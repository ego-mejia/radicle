import { Plus, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button, IconButton } from '../../../../components/ui/Button';
import { Input, Select } from '../../../../components/ui/Input';
import { freshRef, slug } from '../../../../lib/workflow';
import {
  CUSTOM_FIELD_TYPES,
  TICKET_TYPES,
  type CustomFieldType,
  type FieldConf,
  type TicketType,
} from '../../../../services/api/types';
import * as S from './style';

type Props = { fields: FieldConf[]; onChange: (fields: FieldConf[]) => void; readOnly: boolean };

/** Custom fields a template gives its projects. Removing one archives it in projects. */
export function ConfigFieldsEditor({ fields, onChange, readOnly }: Props) {
  const { t } = useTranslation();
  const update = (ref: string, patch: Partial<FieldConf>) =>
    onChange(fields.map((f) => (f.ref === ref ? { ...f, ...patch } : f)));
  const add = () => {
    const name = t('fields.new');
    const ref = freshRef(
      name,
      fields.map((f) => f.ref),
    );
    onChange([
      ...fields,
      { ref, key: slug(name).slice(0, 40), name, field_type: 'text', options: [] },
    ]);
  };
  const types = (f: FieldConf): TicketType[] => f.applies_to_types ?? [...TICKET_TYPES];

  return (
    <S.List>
      {fields.length === 0 && <S.Muted>{t('fields.empty')}</S.Muted>}
      {fields.map((f) => (
        <S.Card key={f.ref}>
          <S.Line>
            <Input
              aria-label={t('fields.name')}
              value={f.name}
              disabled={readOnly}
              onChange={(e) => update(f.ref, { name: e.target.value })}
            />
            <S.Mono
              aria-label={t('fields.key')}
              value={f.key}
              disabled={readOnly}
              onChange={(e) => update(f.ref, { key: e.target.value.toLowerCase() })}
            />
            <Select
              aria-label={t('fields.type')}
              value={f.field_type}
              disabled={readOnly}
              onChange={(e) => update(f.ref, { field_type: e.target.value as CustomFieldType })}
            >
              {CUSTOM_FIELD_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`fields.types.${type}`)}
                </option>
              ))}
            </Select>
            {!readOnly && (
              <IconButton
                label={t('common.remove')}
                onClick={() => onChange(fields.filter((x) => x.ref !== f.ref))}
              >
                <Trash2 />
              </IconButton>
            )}
          </S.Line>
          {f.field_type === 'select' && (
            <Input
              aria-label={t('fields.options')}
              placeholder={t('fields.optionsCsv')}
              disabled={readOnly}
              defaultValue={(f.options ?? []).map((o) => o.value).join(', ')}
              onBlur={(e) =>
                update(f.ref, {
                  options: e.target.value
                    .split(',')
                    .map((v) => v.trim())
                    .filter(Boolean)
                    .map((value) => ({
                      value,
                      label: f.options?.find((o) => o.value === value)?.label ?? value,
                      color: f.options?.find((o) => o.value === value)?.color ?? null,
                    })),
                })
              }
            />
          )}
          <S.Line>
            {TICKET_TYPES.map((type) => (
              <S.Check key={type}>
                <input
                  type="checkbox"
                  disabled={readOnly}
                  checked={types(f).includes(type)}
                  onChange={() => {
                    const current = types(f);
                    const next = current.includes(type)
                      ? current.filter((x) => x !== type)
                      : [...current, type];
                    update(f.ref, { applies_to_types: next });
                  }}
                />
                {t(`ticket.types.${type}`)}
              </S.Check>
            ))}
            {f.applies_to_areas && <Badge>{f.applies_to_areas.join(', ')}</Badge>}
          </S.Line>
        </S.Card>
      ))}
      {!readOnly && (
        <Button size="sm" onClick={add}>
          <Plus />
          {t('fields.new')}
        </Button>
      )}
    </S.List>
  );
}
