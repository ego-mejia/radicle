import { Link } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { formatDateTime, relativeTime } from '../../../../lib/format';
import {
  PRIORITIES,
  type Priority,
  type ProjectDetail,
  type Ticket,
} from '../../../../services/api/types';
import type { TicketActions } from '../../hooks/useTicket';
import { CustomFieldRows } from './components/CustomFieldRows';
import { FieldRow, InlineInput, InlineSelect } from './components/FieldRow';
import { PersonChip, PersonSelect } from './components/PeopleField';
import { TagsField } from './components/TagsField';
import * as S from './style';

type Props = {
  ticket: Ticket;
  project: ProjectDetail | undefined;
  actions: TicketActions;
  canEdit: boolean;
};

/** Every fixed field, editable in place. */
export function FieldsPanel({ ticket, project, actions, canEdit }: Props) {
  const { t } = useTranslation();
  const people = (project?.members ?? []).filter((m) => m.role !== 'viewer' && m.is_active);
  const patch = actions.patch.mutate;
  const openMilestones = (project?.milestones ?? []).filter(
    (m) => m.status === 'open' || m.name === ticket.milestone,
  );
  const notCollaborating = people.filter(
    (p) => !ticket.collaborators.some((c) => c.handle === p.handle),
  );

  return (
    <S.Panel aria-label={t('ticket.fields.status')}>
      <FieldRow label={t('ticket.fields.type')}>
        <S.Muted>{t(`ticket.types.${ticket.type}`)}</S.Muted>
      </FieldRow>
      {ticket.resolution && (
        <FieldRow label={t('ticket.fields.resolution')}>
          {t(`ticket.resolutions.${ticket.resolution}`)}
        </FieldRow>
      )}
      <FieldRow label={t('ticket.fields.priority')}>
        <InlineSelect
          label={t('ticket.fields.priority')}
          value={ticket.priority}
          disabled={!canEdit}
          onChange={(value) => patch({ priority: value as Priority })}
          options={PRIORITIES.map((p) => ({ value: p, label: t(`ticket.priorities.${p}`) }))}
        />
      </FieldRow>
      <FieldRow label={t('ticket.fields.area')}>
        <InlineSelect
          label={t('ticket.fields.area')}
          value={ticket.area ?? ''}
          disabled={!canEdit}
          onChange={(value) => patch({ area: value || null })}
          options={[
            ...(ticket.type === 'draft' || !ticket.area
              ? [{ value: '', label: t('ticket.noArea') }]
              : []),
            ...(project?.areas ?? []).map((a) => ({ value: a.name, label: a.name })),
          ]}
        />
      </FieldRow>
      <FieldRow label={t('ticket.fields.milestone')}>
        <InlineSelect
          label={t('ticket.fields.milestone')}
          value={ticket.milestone ?? ''}
          disabled={!canEdit}
          onChange={(value) => patch({ milestone: value || null })}
          options={[
            { value: '', label: t('ticket.noMilestone') },
            ...openMilestones.map((m) => ({ value: m.name, label: m.name })),
          ]}
        />
      </FieldRow>
      <FieldRow label={t('ticket.fields.assignee')}>
        <PersonSelect
          label={t('ticket.fields.assignee')}
          people={people}
          value={ticket.assignee?.handle ?? ''}
          disabled={!canEdit}
          emptyLabel={t('ticket.unassigned')}
          onChange={(handle) => patch({ assignee: handle || null })}
        />
      </FieldRow>
      <FieldRow label={t('ticket.fields.collaborators')}>
        {ticket.collaborators.map((person) => (
          <PersonChip
            key={person.handle}
            person={person}
            onRemove={canEdit ? () => actions.removeCollaborator.mutate(person.handle) : undefined}
          />
        ))}
        {canEdit && notCollaborating.length > 0 && (
          <InlineSelect
            label={t('ticket.addCollaborator')}
            value=""
            onChange={(handle) => handle && actions.addCollaborator.mutate(handle)}
            options={[
              { value: '', label: `+ ${t('common.add')}` },
              ...notCollaborating.map((p) => ({ value: p.handle, label: `@${p.handle}` })),
            ]}
          />
        )}
      </FieldRow>
      <FieldRow label={t('ticket.fields.reporter')}>
        <PersonChip person={ticket.reporter} />
      </FieldRow>
      <FieldRow label={t('ticket.fields.due')}>
        <InlineInput
          label={t('ticket.fields.due')}
          type="date"
          value={ticket.due_date ?? ''}
          disabled={!canEdit}
          onCommit={(value) => patch({ due_date: value || null })}
        />
      </FieldRow>
      <FieldRow label={t('ticket.fields.estimate')}>
        <InlineInput
          label={t('ticket.fields.estimate')}
          type="number"
          value={ticket.estimate_hours?.toString() ?? ''}
          disabled={!canEdit}
          placeholder="—"
          onCommit={(value) => patch({ estimate_hours: value === '' ? null : Number(value) })}
        />
      </FieldRow>
      <FieldRow label={t('ticket.fields.tags')}>
        <TagsField tags={ticket.tags} disabled={!canEdit} onChange={(tags) => patch({ tags })} />
      </FieldRow>
      <FieldRow label={t('ticket.fields.parent')}>
        {ticket.parent ? (
          <Link to="/t/$key" params={{ key: ticket.parent.key }}>
            <S.ParentLink as="span">{ticket.parent.key}</S.ParentLink> {ticket.parent.title}
          </Link>
        ) : (
          <InlineInput
            label={t('ticket.fields.parent')}
            value=""
            disabled={!canEdit}
            placeholder="—"
            onCommit={(value) => value.trim() && patch({ parent: value.trim().toUpperCase() })}
          />
        )}
      </FieldRow>
      <CustomFieldRows
        ticket={ticket}
        fields={project?.custom_fields ?? []}
        people={people}
        canEdit={canEdit}
        onChange={(key, value) => patch({ custom_fields: { [key]: value } })}
      />
      <FieldRow label={t('ticket.fields.created')}>
        <S.Muted title={formatDateTime(ticket.created_at)}>
          {relativeTime(ticket.created_at)}
        </S.Muted>
      </FieldRow>
      <FieldRow label={t('ticket.fields.updated')}>
        <S.Muted title={formatDateTime(ticket.updated_at)}>
          {relativeTime(ticket.updated_at)}
        </S.Muted>
      </FieldRow>
    </S.Panel>
  );
}
