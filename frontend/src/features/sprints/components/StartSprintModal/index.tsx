import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Textarea } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import type { SprintFields } from '../../../../services/api/sprints';
import { isoPlus, sprintDays } from '../../../../lib/sprints';
import type { Sprint } from '../../../../services/api/types';
import * as S from './style';

const MAX_DAYS = 28;

type Props = {
  sprint: Sprint;
  error?: string | null;
  pending?: boolean;
  onCancel: () => void;
  onStart: (body: SprintFields) => void;
};

/** Name, goal, dates (1 to 28 days) and optional capacity before starting. */
export function StartSprintModal({ sprint, error, pending, onCancel, onStart }: Props) {
  const { t } = useTranslation();
  const [name, setName] = useState(sprint.name);
  const [goal, setGoal] = useState(sprint.goal ?? '');
  const [start, setStart] = useState(sprint.start_date ?? isoPlus(0));
  const [end, setEnd] = useState(sprint.end_date ?? isoPlus(13));
  const [capacity, setCapacity] = useState(
    sprint.capacity_hours != null ? String(sprint.capacity_hours) : '',
  );
  const days = start && end ? sprintDays(start, end) : 0;
  const invalid = !start || !end || days < 1 || days > MAX_DAYS;
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onCancel()}
      title={t('sprints.startTitle', { name: sprint.name })}
      footer={
        <>
          <Button onClick={onCancel}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            disabled={invalid || pending}
            onClick={() =>
              onStart({
                name,
                goal: goal || null,
                start_date: start,
                end_date: end,
                capacity_hours: capacity ? Number(capacity) : null,
              })
            }
          >
            {t('sprints.start')}
          </Button>
        </>
      }
    >
      <S.Form>
        <Field label={t('sprints.name')}>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label={t('sprints.goal')}>
          <Textarea rows={2} value={goal} onChange={(e) => setGoal(e.target.value)} />
        </Field>
        <S.Dates>
          <Field label={t('sprints.startDate')}>
            <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          </Field>
          <Field
            label={t('sprints.endDate')}
            error={days > MAX_DAYS || (end && days < 1) ? t('sprints.duration', { days }) : null}
          >
            <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
          </Field>
        </S.Dates>
        <Field label={t('sprints.capacityHours')} hint={t('sprints.capacityHint')}>
          <Input
            type="number"
            min={0}
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
          />
        </Field>
        <FormError>{error}</FormError>
      </S.Form>
    </Modal>
  );
}
