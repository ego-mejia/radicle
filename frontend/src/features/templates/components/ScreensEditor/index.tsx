import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Tabs } from '../../../../components/ui/Tabs';
import { TICKET_TYPES, type TicketType, type WorkflowConf } from '../../../../services/api/types';
import * as S from './style';

export type ScreenField = { field: string; required?: boolean };
export type ScreenConf = {
  type: TicketType;
  operation: string;
  transition?: string | null;
  fields?: ScreenField[];
};

const FIXED = [
  'title',
  'description_md',
  'priority',
  'area',
  'milestone',
  'assignee',
  'collaborators',
  'parent',
  'start_date',
  'due_date',
  'estimate_hours',
  'tags',
];

type Props = {
  screens: ScreenConf[];
  workflows: Partial<Record<TicketType, WorkflowConf>>;
  /** Custom fields by key with the types they apply to. */
  customFields: { key: string; name: string; types: TicketType[] }[];
  onChange: (screens: ScreenConf[]) => void;
  readOnly: boolean;
};

type Operation = { operation: string; transition: string | null; label: string };

/** Which fields each form asks for, per type: create, edit and every transition. */
export function ScreensEditor({ screens, workflows, customFields, onChange, readOnly }: Props) {
  const { t } = useTranslation();
  const [type, setType] = useState<TicketType>('task');
  const operations: Operation[] = [
    { operation: 'create', transition: null, label: t('screens.create') },
    { operation: 'edit', transition: null, label: t('screens.edit') },
    ...(workflows[type]?.transitions ?? []).map((tr) => ({
      operation: 'transition',
      transition: tr.ref,
      label: t('screens.transition', { name: tr.name }),
    })),
  ];
  const available = [
    ...FIXED.map((f) => ({
      field: f,
      label: t(`rules.fields.${f}`, f === 'title' ? t('ticket.fields.title') : f),
    })),
    ...customFields
      .filter((f) => f.types.includes(type))
      .map((f) => ({ field: `cf.${f.key}`, label: f.name })),
  ];
  const find = (op: Operation) =>
    screens.find(
      (s) =>
        s.type === type && s.operation === op.operation && (s.transition ?? null) === op.transition,
    );
  const replace = (op: Operation, next: ScreenConf | null) => {
    const rest = screens.filter((s) => s !== find(op));
    onChange(next ? [...rest, next] : rest);
  };

  return (
    <S.Wrapper>
      <Tabs
        label={t('screens.title')}
        value={type}
        onChange={setType}
        tabs={TICKET_TYPES.map((id) => ({ id, label: t(`ticket.types.${id}`) }))}
      />
      <S.Help>{t('screens.help')}</S.Help>
      {operations.map((op) => {
        const screen = find(op);
        const fields = screen?.fields ?? [];
        return (
          <S.Card key={`${op.operation}-${op.transition ?? ''}`} aria-label={op.label}>
            <S.Head>
              <strong>{op.label}</strong>
              <label>
                <input
                  type="checkbox"
                  disabled={readOnly}
                  checked={Boolean(screen)}
                  onChange={(e) =>
                    replace(
                      op,
                      e.target.checked
                        ? {
                            type,
                            operation: op.operation,
                            transition: op.transition,
                            fields:
                              op.operation === 'transition'
                                ? []
                                : [{ field: 'title', required: true }],
                          }
                        : null,
                    )
                  }
                />
                {t('screens.custom')}
              </label>
            </S.Head>
            {!screen ? (
              <S.Muted>
                {op.operation === 'transition' ? t('screens.noFields') : t('screens.defaults')}
              </S.Muted>
            ) : (
              <S.Fields>
                {available.map(({ field, label }) => {
                  const entry = fields.find((f) => f.field === field);
                  const update = (next: ScreenField | null) =>
                    replace(op, {
                      ...screen,
                      fields: next
                        ? entry
                          ? fields.map((f) => (f.field === field ? next : f))
                          : [...fields, next]
                        : fields.filter((f) => f.field !== field),
                    });
                  return (
                    <S.FieldRow key={field}>
                      <label>
                        <input
                          type="checkbox"
                          aria-label={t('screens.show', { field: label })}
                          disabled={readOnly}
                          checked={Boolean(entry)}
                          onChange={(e) =>
                            update(e.target.checked ? { field, required: false } : null)
                          }
                        />
                        {label}
                      </label>
                      <label>
                        <input
                          type="checkbox"
                          aria-label={t('screens.requiredFor', { field: label })}
                          disabled={readOnly || !entry}
                          checked={Boolean(entry?.required)}
                          onChange={(e) =>
                            entry && update({ ...entry, required: e.target.checked })
                          }
                        />
                        {t('screens.required')}
                      </label>
                    </S.FieldRow>
                  );
                })}
              </S.Fields>
            )}
          </S.Card>
        );
      })}
    </S.Wrapper>
  );
}
