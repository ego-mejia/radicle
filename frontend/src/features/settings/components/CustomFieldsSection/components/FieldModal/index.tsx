import { useMutation } from '@tanstack/react-query';
import { Plus, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../../../components/ui/Button';
import { Field, FormError } from '../../../../../../components/ui/Field';
import { Input, Select } from '../../../../../../components/ui/Input';
import { Modal } from '../../../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../../../hooks/useErrorMessage';
import { createField, patchField } from '../../../../../../services/api/fields';
import {
  CUSTOM_FIELD_TYPES,
  TICKET_TYPES,
  type CustomField,
  type CustomFieldType,
  type ProjectDetail,
  type TicketType,
} from '../../../../../../services/api/types';
import * as S from './style';

type Option = { value: string; label: string; color: string | null };
type Props = { project: ProjectDetail; field: CustomField | null; onClose: () => void };

function slug(name: string): string {
  return name
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^[^a-z]+|_+$/g, '')
    .slice(0, 40);
}

/** Create a custom field, or edit one (its key and type are fixed once created). */
export function FieldModal({ project, field, onClose }: Props) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const [name, setName] = useState(field?.name ?? '');
  const [key, setKey] = useState(field?.key ?? '');
  const [keyTouched, setKeyTouched] = useState(Boolean(field));
  const [type, setType] = useState<CustomFieldType>(field?.field_type ?? 'text');
  const [options, setOptions] = useState<Option[]>(
    field?.options.map((o) => ({ ...o })) ?? [{ value: '', label: '', color: null }],
  );
  const [types, setTypes] = useState<TicketType[]>(field?.applies_to_types ?? [...TICKET_TYPES]);
  const [areas, setAreas] = useState<string[] | null>(field?.applies_to_areas ?? null);

  const save = useMutation({
    mutationFn: () => {
      const body = {
        name,
        applies_to_types: types,
        applies_to_areas: areas,
        options:
          type === 'select'
            ? options
                .filter((o) => o.value.trim())
                .map((o) => ({ value: o.value.trim(), label: o.label || null, color: o.color }))
            : null,
      };
      return field
        ? patchField(project.key, field.key, body)
        : createField(project.key, { ...body, key, field_type: type });
    },
    onSuccess: onClose,
  });

  const toggleType = (value: TicketType) =>
    setTypes((prev) => (prev.includes(value) ? prev.filter((x) => x !== value) : [...prev, value]));
  const toggleArea = (value: string) =>
    setAreas((prev) => {
      const list = prev ?? [];
      return list.includes(value) ? list.filter((x) => x !== value) : [...list, value];
    });
  const setOption = (index: number, patch: Partial<Option>) =>
    setOptions((prev) => prev.map((o, i) => (i === index ? { ...o, ...patch } : o)));

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={field ? t('fields.edit') : t('fields.new')}
      width={560}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button variant="primary" type="submit" form="field-form" disabled={save.isPending}>
            {field ? t('common.save') : t('common.create')}
          </Button>
        </>
      }
    >
      <S.Form
        id="field-form"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <FormError>{save.error ? errorMessage(save.error) : null}</FormError>
        <Field label={t('fields.name')}>
          <Input
            value={name}
            required
            autoFocus
            onChange={(e) => {
              setName(e.target.value);
              if (!keyTouched) setKey(slug(e.target.value));
            }}
          />
        </Field>
        <S.Pair>
          <Field label={t('fields.key')} hint={t('fields.keyHint')}>
            <S.Mono
              value={key}
              required
              disabled={Boolean(field)}
              pattern="[a-z][a-z0-9_]{1,39}"
              onChange={(e) => {
                setKeyTouched(true);
                setKey(e.target.value.toLowerCase());
              }}
            />
          </Field>
          <Field label={t('fields.type')}>
            <Select
              value={type}
              disabled={Boolean(field)}
              onChange={(e) => setType(e.target.value as CustomFieldType)}
            >
              {CUSTOM_FIELD_TYPES.map((value) => (
                <option key={value} value={value}>
                  {t(`fields.types.${value}`)}
                </option>
              ))}
            </Select>
          </Field>
        </S.Pair>
        {type === 'select' && (
          <Field label={t('fields.options')} group>
            <S.Options>
              {options.map((o, i) => (
                <S.OptionRow key={i}>
                  <S.Swatch
                    type="color"
                    aria-label={t('settings.color')}
                    value={o.color ?? '#9CA3AF'}
                    onChange={(e) => setOption(i, { color: e.target.value.toUpperCase() })}
                  />
                  <Input
                    aria-label={t('fields.optionValue')}
                    placeholder={t('fields.optionValue')}
                    value={o.value}
                    onChange={(e) => setOption(i, { value: e.target.value })}
                  />
                  <Input
                    aria-label={t('fields.optionLabel')}
                    placeholder={t('fields.optionLabel')}
                    value={o.label}
                    onChange={(e) => setOption(i, { label: e.target.value })}
                  />
                  <IconButton
                    label={t('common.remove')}
                    onClick={() => setOptions((prev) => prev.filter((_, j) => j !== i))}
                  >
                    <X />
                  </IconButton>
                </S.OptionRow>
              ))}
              <Button
                size="sm"
                onClick={() =>
                  setOptions((prev) => [...prev, { value: '', label: '', color: null }])
                }
              >
                <Plus />
                {t('fields.addOption')}
              </Button>
            </S.Options>
          </Field>
        )}
        <Field label={t('fields.appliesToTypes')} group>
          <S.Checks>
            {TICKET_TYPES.map((value) => (
              <label key={value}>
                <input
                  type="checkbox"
                  checked={types.includes(value)}
                  onChange={() => toggleType(value)}
                />
                {t(`ticket.types.${value}`)}
              </label>
            ))}
          </S.Checks>
        </Field>
        <Field label={t('fields.appliesToAreas')} group>
          <S.Checks>
            <label>
              <input
                type="checkbox"
                checked={areas === null}
                onChange={() => setAreas(areas === null ? [] : null)}
              />
              {t('fields.allAreas')}
            </label>
            {areas !== null &&
              project.areas.map((a) => (
                <label key={a.name}>
                  <input
                    type="checkbox"
                    checked={areas.includes(a.name)}
                    onChange={() => toggleArea(a.name)}
                  />
                  {a.name}
                </label>
              ))}
          </S.Checks>
        </Field>
      </S.Form>
    </Modal>
  );
}
