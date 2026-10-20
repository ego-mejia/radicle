import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { TypeIcon } from '../../../../components/icons/TypeIcon';
import { type EditorApi, MarkdownEditor } from '../../../../components/Markdown/MarkdownEditor';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import type { CreateTicketDefaults } from '../../../../contexts/createTicket';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useMe } from '../../../../hooks/useMe';
import { useToast } from '../../../../hooks/useToast';
import { missingRequired, toBody, type Values } from '../../../../lib/schemaForm';
import { ApiError } from '../../../../services/api/client';
import { projectKeys } from '../../../../services/api/projects';
import { fetchSchema, screenKeys } from '../../../../services/api/screens';
import { createTicket, ticketKeys } from '../../../../services/api/tickets';
import {
  CLASSIFICATIONS,
  type Classification,
  TICKET_TYPES,
  type TicketCreate,
  type TicketType,
} from '../../../../services/api/types';
import { useProject } from '../../../projects/hooks/useProject';
import { usePendingFiles } from '../../hooks/usePendingFiles';
import { SchemaFields } from '../SchemaFields';
import { PendingFiles } from './components/PendingFiles';
import * as S from './style';

type Props = { defaults: CreateTicketDefaults; onClose: () => void };

const initial = (defaults: CreateTicketDefaults): Values => ({
  title: '',
  description_md: '',
  priority: 'medium',
  area: defaults.area ?? null,
  milestone: defaults.milestone ?? null,
  parent: defaults.parent ?? null,
});

/** Create a ticket. The fields come from the project's create screen (or the defaults). */
export function CreateTicketModal({ defaults, onClose }: Props) {
  const { t } = useTranslation();
  const me = useMe();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const writable = (me.projects ?? []).filter((p) => p.permissions.includes('ticket.create'));
  const [projectKey, setProjectKey] = useState(
    writable.some((p) => p.key === defaults.project) ? defaults.project! : (writable[0]?.key ?? ''),
  );
  const { data: project } = useProject(projectKey);
  const [type, setType] = useState<TicketType>('task');
  const [classification, setClassification] = useState<Classification>('idea');
  const [values, setValues] = useState<Values>(() => initial(defaults));
  const [another, setAnother] = useState(false);
  const [checked, setChecked] = useState(false);
  const editor = useRef<EditorApi | null>(null);
  const pending = usePendingFiles(editor);
  const { data: schema } = useQuery({
    queryKey: screenKeys.schema(projectKey, type, 'create'),
    queryFn: () => fetchSchema(projectKey, type, 'create'),
    enabled: Boolean(projectKey),
  });
  const fields = schema?.fields ?? [];
  const area = (values.area as string | null) ?? null;
  const missing = missingRequired(fields, values, area);
  const set = (name: string, value: unknown) => setValues((v) => ({ ...v, [name]: value }));

  const mutation = useMutation({
    mutationFn: () => {
      const { body, custom } = toBody(values);
      return createTicket(projectKey, {
        ...(body as Partial<TicketCreate>),
        type,
        title: String(values.title ?? ''),
        custom_fields: custom,
        classification: type === 'draft' ? classification : null,
      } as TicketCreate);
    },
    onSuccess: async (ticket) => {
      await pending.flush(ticket).catch((error) => toast(errorMessage(error), 'error'));
      await queryClient.invalidateQueries({ queryKey: ticketKeys.all });
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
      toast(
        t('create.created', { key: ticket.key }),
        'info',
        <Button
          size="sm"
          variant="ghost"
          onClick={() => void navigate({ to: '/t/$key', params: { key: ticket.key } })}
        >
          {t('common.seeAll')}
        </Button>,
      );
      setChecked(false);
      if (another) setValues((v) => ({ ...v, title: '', description_md: '' }));
      else onClose();
    },
  });

  const submit = () => {
    setChecked(true);
    if (missing.length === 0) mutation.mutate();
  };
  const serverErrors =
    mutation.error instanceof ApiError
      ? Object.fromEntries(mutation.error.problem.errors.map((e) => [e.field ?? '', e.message]))
      : {};
  const errors: Record<string, string | undefined> = { ...serverErrors };
  if (checked) for (const f of missing) errors[f.field] = t('create.required');
  const mentions = (project?.members ?? []).map((m) => ({
    handle: m.handle,
    name: m.display_name,
  }));
  const required = fields.filter((f) => f.required);
  const optional = fields.filter((f) => !f.required);
  const shownError =
    mutation.error && !Object.keys(serverErrors).some((f) => fields.some((x) => x.field === f))
      ? errorMessage(mutation.error)
      : null;

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={t('create.title')}
      width={640}
      footer={
        <>
          <S.Another>
            <input
              type="checkbox"
              checked={another}
              onChange={(e) => setAnother(e.target.checked)}
            />
            {t('create.createAnother')}
          </S.Another>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            type="submit"
            form="create-ticket"
            data-tour="ticket-form.submit"
            disabled={mutation.isPending || !projectKey}
          >
            {t('create.submit')}
          </Button>
        </>
      }
    >
      <S.Form
        id="create-ticket"
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <FormError>{shownError}</FormError>
        <S.Row>
          <Field label={t('create.project')}>
            <Select value={projectKey} onChange={(e) => setProjectKey(e.target.value)}>
              {writable.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.key} · {p.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t('ticket.fields.type')} group>
            <S.Types
              role="radiogroup"
              aria-label={t('ticket.fields.type')}
              data-tour="ticket-form.type"
            >
              {TICKET_TYPES.map((value) => (
                <S.TypeOption
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={type === value}
                  $active={type === value}
                  onClick={() => setType(value)}
                >
                  <TypeIcon type={value} />
                  {t(`ticket.types.${value}`)}
                </S.TypeOption>
              ))}
            </S.Types>
          </Field>
        </S.Row>
        {type === 'draft' && (
          <Field label={`${t('inbox.classification')} *`} error={errors.classification}>
            <Select
              value={classification}
              onChange={(e) => setClassification(e.target.value as Classification)}
            >
              {CLASSIFICATIONS.map((c) => (
                <option key={c} value={c}>
                  {t(`inbox.classifications.${c}`)}
                </option>
              ))}
            </Select>
          </Field>
        )}
        <Field label={`${t('ticket.fields.title')} *`} error={errors.title}>
          <Input
            data-tour="ticket-form.title"
            value={String(values.title ?? '')}
            onChange={(e) => set('title', e.target.value)}
            placeholder={t('create.titlePlaceholder')}
            autoFocus
            maxLength={255}
          />
        </Field>
        <SchemaFields
          fields={required}
          values={values}
          onChange={set}
          errors={errors}
          area={area}
        />
        {fields.some((f) => f.field === 'description_md') && (
          <Field label={t('ticket.fields.description')}>
            <MarkdownEditor
              value={String(values.description_md ?? '')}
              onChange={(value) => set('description_md', value)}
              mentions={mentions}
              placeholder={t('create.descriptionPlaceholder')}
              ariaLabel={t('ticket.fields.description')}
              onSubmit={submit}
              onFiles={pending.add}
              apiRef={editor}
            />
            <PendingFiles files={pending.files} onRemove={pending.remove} />
          </Field>
        )}
        {optional.length > 0 && (
          <S.More open={Boolean(defaults.parent || defaults.milestone)}>
            <summary>{t('create.moreFields')}</summary>
            <div>
              <SchemaFields
                fields={optional}
                values={values}
                onChange={set}
                errors={errors}
                area={area}
              />
            </div>
          </S.More>
        )}
      </S.Form>
    </Modal>
  );
}
