import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Select } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { PRIORITIES, type Priority, type ProjectDetail } from '../../../../services/api/types';
import { assignable } from '../../../projects/hooks/useProject';

export type Approval = {
  type: 'task' | 'bug';
  area: string;
  milestone: string | null;
  priority: Priority | null;
  assignee: string | null;
};

type Props = {
  ticketKey: string;
  project: ProjectDetail;
  pending: boolean;
  error: string | null;
  onCancel: () => void;
  onApprove: (value: Approval) => void;
};

/** Approve and convert: target type and area (required), and optional details. */
export function ApproveDialog({ ticketKey, project, pending, error, onCancel, onApprove }: Props) {
  const { t } = useTranslation();
  const areas = project.areas.filter((a) => !a.archived);
  const [value, setValue] = useState<Approval>({
    type: 'task',
    area: areas[0]?.name ?? '',
    milestone: null,
    priority: null,
    assignee: null,
  });
  const set = (patch: Partial<Approval>) => setValue((v) => ({ ...v, ...patch }));
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onCancel()}
      title={t('inbox.approveTitle', { key: ticketKey })}
      footer={
        <>
          <Button onClick={onCancel}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            disabled={pending || !value.area}
            onClick={() => onApprove(value)}
          >
            {t('inbox.approve')}
          </Button>
        </>
      }
    >
      <p>{t('inbox.approveHelp')}</p>
      <Field label={t('inbox.convertTo')}>
        <Select
          value={value.type}
          onChange={(e) => set({ type: e.target.value as Approval['type'] })}
        >
          <option value="task">{t('ticket.types.task')}</option>
          <option value="bug">{t('ticket.types.bug')}</option>
        </Select>
      </Field>
      <Field label={`${t('ticket.fields.area')} *`}>
        <Select value={value.area} onChange={(e) => set({ area: e.target.value })}>
          {areas.map((a) => (
            <option key={a.name} value={a.name}>
              {a.name}
            </option>
          ))}
        </Select>
      </Field>
      <Field label={t('ticket.fields.milestone')}>
        <Select
          value={value.milestone ?? ''}
          onChange={(e) => set({ milestone: e.target.value || null })}
        >
          <option value="">—</option>
          {project.milestones
            .filter((m) => m.status === 'open')
            .map((m) => (
              <option key={m.name} value={m.name}>
                {m.name}
              </option>
            ))}
        </Select>
      </Field>
      <Field label={t('ticket.fields.priority')}>
        <Select
          value={value.priority ?? ''}
          onChange={(e) => set({ priority: (e.target.value || null) as Priority | null })}
        >
          <option value="">—</option>
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {t(`ticket.priorities.${p}`)}
            </option>
          ))}
        </Select>
      </Field>
      <Field label={t('ticket.fields.assignee')}>
        <Select
          value={value.assignee ?? ''}
          onChange={(e) => set({ assignee: e.target.value || null })}
        >
          <option value="">—</option>
          {assignable(project.members).map((m) => (
            <option key={m.handle} value={m.handle}>
              {m.display_name} (@{m.handle})
            </option>
          ))}
        </Select>
      </Field>
      <FormError>{error}</FormError>
    </Modal>
  );
}
