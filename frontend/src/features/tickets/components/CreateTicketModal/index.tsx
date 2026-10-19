import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { TypeIcon } from '../../../../components/icons/TypeIcon';
import { MarkdownEditor } from '../../../../components/Markdown/MarkdownEditor';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import type { CreateTicketDefaults } from '../../../../contexts/createTicket';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useMe } from '../../../../hooks/useMe';
import { useToast } from '../../../../hooks/useToast';
import { ApiError } from '../../../../services/api/client';
import { projectKeys } from '../../../../services/api/projects';
import { createTicket, ticketKeys } from '../../../../services/api/tickets';
import {
  PRIORITIES,
  TICKET_TYPES,
  type Priority,
  type TicketType,
} from '../../../../services/api/types';
import { useProject } from '../../../projects/hooks/useProject';
import * as S from './style';

type Props = { defaults: CreateTicketDefaults; onClose: () => void };

const blank = (defaults: CreateTicketDefaults) => ({
  type: 'task' as TicketType,
  title: '',
  description_md: '',
  area: defaults.area ?? '',
  priority: 'medium' as Priority,
  milestone: defaults.milestone ?? '',
  assignee: '',
  parent: defaults.parent ?? '',
  due_date: '',
  estimate_hours: '',
  tags: '',
});

export function CreateTicketModal({ defaults, onClose }: Props) {
  const { t } = useTranslation();
  const me = useMe();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const writable = (me.projects ?? []).filter((p) => p.role !== 'viewer');
  const [projectKey, setProjectKey] = useState(
    writable.some((p) => p.key === defaults.project) ? defaults.project! : (writable[0]?.key ?? ''),
  );
  const { data: project } = useProject(projectKey);
  const [form, setForm] = useState(() => blank(defaults));
  const [another, setAnother] = useState(false);
  const set = <K extends keyof typeof form>(name: K, value: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [name]: value }));

  const mutation = useMutation({
    mutationFn: () =>
      createTicket(projectKey, {
        type: form.type,
        title: form.title,
        description_md: form.description_md,
        area: form.area || null,
        priority: form.priority,
        milestone: form.milestone || null,
        assignee: form.assignee || null,
        parent: form.parent || null,
        due_date: form.due_date || null,
        estimate_hours: form.estimate_hours === '' ? null : Number(form.estimate_hours),
        tags: form.tags.split(/[\s,]+/).filter(Boolean),
      }),
    onSuccess: async (ticket) => {
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
      if (another) setForm((f) => ({ ...f, title: '', description_md: '' }));
      else onClose();
    },
  });

  const fieldError = (name: string) =>
    mutation.error instanceof ApiError
      ? mutation.error.problem.errors.find((e) => e.field === name)?.message
      : undefined;
  const people = (project?.members ?? []).filter((m) => m.role !== 'viewer');
  const mentions = (project?.members ?? []).map((m) => ({
    handle: m.handle,
    name: m.display_name,
  }));

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={t('create.title')}
      width={620}
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
            disabled={mutation.isPending || !projectKey}
          >
            {t('create.submit')}
          </Button>
        </>
      }
    >
      <S.Form
        id="create-ticket"
        onSubmit={(e) => {
          e.preventDefault();
          mutation.mutate();
        }}
      >
        <FormError>
          {mutation.error && !fieldError('area') && !fieldError('title')
            ? errorMessage(mutation.error)
            : null}
        </FormError>
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
            <S.Types role="radiogroup" aria-label={t('ticket.fields.type')}>
              {TICKET_TYPES.map((type) => (
                <S.TypeOption
                  key={type}
                  type="button"
                  role="radio"
                  aria-checked={form.type === type}
                  $active={form.type === type}
                  onClick={() => set('type', type)}
                >
                  <TypeIcon type={type} />
                  {t(`ticket.types.${type}`)}
                </S.TypeOption>
              ))}
            </S.Types>
          </Field>
        </S.Row>
        <Field label={t('ticket.fields.title')} error={fieldError('title')}>
          <Input
            value={form.title}
            onChange={(e) => set('title', e.target.value)}
            placeholder={t('create.titlePlaceholder')}
            required
            autoFocus
            maxLength={255}
          />
        </Field>
        <S.Row>
          <Field
            label={
              form.type === 'draft'
                ? `${t('ticket.fields.area')} (${t('common.optional')})`
                : t('ticket.fields.area')
            }
            error={fieldError('area')}
          >
            <Select
              value={form.area}
              onChange={(e) => set('area', e.target.value)}
              required={form.type !== 'draft'}
            >
              <option value="">—</option>
              {project?.areas.map((a) => (
                <option key={a.name} value={a.name}>
                  {a.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t('ticket.fields.priority')}>
            <Select
              value={form.priority}
              onChange={(e) => set('priority', e.target.value as Priority)}
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {t(`ticket.priorities.${p}`)}
                </option>
              ))}
            </Select>
          </Field>
        </S.Row>
        <Field label={t('ticket.fields.description')}>
          <MarkdownEditor
            value={form.description_md}
            onChange={(value) => set('description_md', value)}
            mentions={mentions}
            placeholder={t('create.descriptionPlaceholder')}
            ariaLabel={t('ticket.fields.description')}
            onSubmit={() => mutation.mutate()}
          />
        </Field>
        <S.More open={Boolean(defaults.parent || defaults.milestone)}>
          <summary>{t('create.moreFields')}</summary>
          <div>
            <S.Row>
              <Field label={t('ticket.fields.milestone')}>
                <Select value={form.milestone} onChange={(e) => set('milestone', e.target.value)}>
                  <option value="">{t('ticket.noMilestone')}</option>
                  {project?.milestones
                    .filter((m) => m.status === 'open')
                    .map((m) => (
                      <option key={m.name} value={m.name}>
                        {m.name}
                      </option>
                    ))}
                </Select>
              </Field>
              <Field label={t('ticket.fields.assignee')}>
                <Select value={form.assignee} onChange={(e) => set('assignee', e.target.value)}>
                  <option value="">{t('ticket.unassigned')}</option>
                  {people.map((p) => (
                    <option key={p.handle} value={p.handle}>
                      {p.display_name} (@{p.handle})
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label={t('ticket.fields.parent')} error={fieldError('parent')}>
                <Input
                  value={form.parent}
                  onChange={(e) => set('parent', e.target.value.toUpperCase())}
                  placeholder="PA-1"
                />
              </Field>
              <Field label={t('ticket.fields.due')}>
                <Input
                  type="date"
                  value={form.due_date}
                  onChange={(e) => set('due_date', e.target.value)}
                />
              </Field>
              <Field label={t('ticket.fields.estimate')}>
                <Input
                  type="number"
                  min={0}
                  step="0.5"
                  value={form.estimate_hours}
                  onChange={(e) => set('estimate_hours', e.target.value)}
                />
              </Field>
              <Field label={t('ticket.fields.tags')} error={fieldError('tags')}>
                <Input
                  value={form.tags}
                  onChange={(e) => set('tags', e.target.value)}
                  placeholder="backlog, pagos"
                />
              </Field>
            </S.Row>
          </div>
        </S.More>
      </S.Form>
    </Modal>
  );
}
