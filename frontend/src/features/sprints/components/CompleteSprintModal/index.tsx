import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Select } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import type { Sprint, SprintReport } from '../../../../services/api/types';
import * as S from './style';

type Props = {
  sprint: Sprint;
  report: SprintReport | undefined;
  futureSprints: Sprint[];
  error?: string | null;
  pending?: boolean;
  onCancel: () => void;
  onComplete: (body: { move_unfinished_to: string; tag_backlog: boolean }) => void;
};

/** Summary of the sprint and where its unfinished tickets go. */
export function CompleteSprintModal({
  sprint,
  report,
  futureSprints,
  error,
  pending,
  onCancel,
  onComplete,
}: Props) {
  const { t } = useTranslation();
  const [target, setTarget] = useState('backlog');
  const [tag, setTag] = useState(true);
  const rows = report
    ? ([
        ['completed', report.completed],
        ['notCompleted', report.not_completed],
        ['added', report.added_after_start],
        ['removed', report.removed],
      ] as const)
    : [];
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onCancel()}
      title={t('sprints.completeTitle', { name: sprint.name })}
      footer={
        <>
          <Button onClick={onCancel}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            disabled={pending}
            onClick={() => onComplete({ move_unfinished_to: target, tag_backlog: tag })}
          >
            {t('sprints.complete')}
          </Button>
        </>
      }
    >
      <S.Summary>
        {rows.map(([key, items]) => (
          <div key={key}>
            <dt>{t(`sprints.report.${key}`)}</dt>
            <dd>
              {items.length}
              <small>
                {t('sprints.hours', { hours: items.reduce((s, i) => s + i.estimate_hours, 0) })}
              </small>
            </dd>
          </div>
        ))}
      </S.Summary>
      {report && report.not_completed.length > 0 && (
        <S.Options>
          <Field label={t('sprints.moveUnfinished', { count: report.not_completed.length })}>
            <Select value={target} onChange={(e) => setTarget(e.target.value)}>
              <option value="backlog">{t('sprints.backlog')}</option>
              {futureSprints.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </Select>
          </Field>
          {target === 'backlog' && (
            <label>
              <input type="checkbox" checked={tag} onChange={(e) => setTag(e.target.checked)} />
              {t('sprints.tagBacklog')}
            </label>
          )}
        </S.Options>
      )}
      <FormError>{error}</FormError>
    </Modal>
  );
}
