import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../components/ui/Button';
import { Field, FormError } from '../../../../../../components/ui/Field';
import { Input, Select } from '../../../../../../components/ui/Input';
import { Modal } from '../../../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../../../hooks/useErrorMessage';
import {
  type BulkOperation,
  bulkUpdate,
  fetchJob,
  jobKeys,
} from '../../../../../../services/api/bulk';
import { PRIORITIES, type ProjectDetail } from '../../../../../../services/api/types';
import * as S from './style';

export type BulkAction = 'field' | 'tags' | 'status' | 'assign';
type Result = Awaited<ReturnType<typeof bulkUpdate>>;

const FIELDS = ['priority', 'milestone', 'area', 'due_date'] as const;

type Props = {
  project: ProjectDetail;
  keys: string[];
  action: BulkAction;
  onClose: () => void;
  onDone: () => void;
};

/** Build one operation, preview it with a dry run, then apply it (as a job if large). */
export function BulkDialog({ project, keys, action, onClose, onDone }: Props) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const [field, setField] = useState<(typeof FIELDS)[number]>('milestone');
  const [value, setValue] = useState('');
  const [tagMode, setTagMode] = useState<'add_tag' | 'remove_tag'>('remove_tag');
  const [preview, setPreview] = useState<Result | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const statuses = [...new Set(project.workflows.flatMap((w) => w.statuses.map((s) => s.name)))];
  const people = project.members.filter((m) => m.effective_role !== 'viewer');

  const operation = (): BulkOperation => {
    if (action === 'field')
      return value ? { op: 'set_field', field, value } : { op: 'clear_field', field };
    if (action === 'tags') return { op: tagMode, tag: value.replace(/^#/, '') };
    if (action === 'status') return { op: 'transition', to_status: value };
    return { op: 'assign', handle: value || null };
  };
  const run = useMutation({
    mutationFn: (dryRun: boolean) =>
      bulkUpdate({ keys, operations: [operation()], dry_run: dryRun }),
    onSuccess: (result) => {
      if (result.dry_run) setPreview(result);
      else if (result.job) setJobId(result.job.id);
      else setPreview(result);
    },
  });
  const { data: job } = useQuery({
    queryKey: jobKeys.detail(jobId ?? ''),
    queryFn: () => fetchJob(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (q) =>
      q.state.data && ['succeeded', 'failed'].includes(q.state.data.status) ? false : 1000,
  });
  const applied = preview && !preview.dry_run;
  const finished = applied || (job && ['succeeded', 'failed'].includes(job.status));
  const needsValue = action === 'tags' || action === 'status';

  return (
    <Modal
      open
      onOpenChange={(open) => !open && (finished ? onDone() : onClose())}
      title={t(`bulk.titles.${action}`, { count: keys.length })}
      footer={
        finished ? (
          <Button variant="primary" onClick={onDone}>
            {t('common.close')}
          </Button>
        ) : (
          <>
            <Button onClick={onClose}>{t('common.cancel')}</Button>
            {preview?.dry_run ? (
              <Button
                variant="primary"
                disabled={run.isPending || preview.succeeded === 0 || Boolean(jobId)}
                onClick={() => run.mutate(false)}
              >
                {t('bulk.apply', { count: preview.succeeded })}
              </Button>
            ) : (
              <Button
                variant="primary"
                disabled={run.isPending || (needsValue && !value)}
                onClick={() => run.mutate(true)}
              >
                {t('bulk.preview')}
              </Button>
            )}
          </>
        )
      }
    >
      <FormError>{run.error ? errorMessage(run.error) : null}</FormError>
      {!preview && !jobId && (
        <S.Form>
          {action === 'field' && (
            <>
              <Field label={t('bulk.field')}>
                <Select value={field} onChange={(e) => setField(e.target.value as typeof field)}>
                  {FIELDS.map((f) => (
                    <option key={f} value={f}>
                      {t(`rules.fields.${f}`)}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label={t('bulk.value')} hint={t('bulk.emptyClears')}>
                {field === 'due_date' ? (
                  <Input type="date" value={value} onChange={(e) => setValue(e.target.value)} />
                ) : (
                  <Select value={value} onChange={(e) => setValue(e.target.value)}>
                    <option value="">—</option>
                    {(field === 'priority'
                      ? PRIORITIES
                      : field === 'area'
                        ? project.areas.map((a) => a.name)
                        : project.milestones.filter((m) => m.status === 'open').map((m) => m.name)
                    ).map((o) => (
                      <option key={o} value={o}>
                        {field === 'priority' ? t(`ticket.priorities.${o}`) : o}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
            </>
          )}
          {action === 'tags' && (
            <>
              <Field label={t('bulk.tagMode')}>
                <Select
                  value={tagMode}
                  onChange={(e) => setTagMode(e.target.value as typeof tagMode)}
                >
                  <option value="add_tag">{t('bulk.addTag')}</option>
                  <option value="remove_tag">{t('bulk.removeTag')}</option>
                </Select>
              </Field>
              <Field label={t('rules.tag')}>
                <Input
                  value={value}
                  placeholder="backlog"
                  onChange={(e) => setValue(e.target.value)}
                />
              </Field>
            </>
          )}
          {action === 'status' && (
            <Field label={t('bulk.toStatus')}>
              <Select value={value} onChange={(e) => setValue(e.target.value)}>
                <option value="">—</option>
                {statuses.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            </Field>
          )}
          {action === 'assign' && (
            <Field label={t('ticket.fields.assignee')}>
              <Select value={value} onChange={(e) => setValue(e.target.value)}>
                <option value="">{t('ticket.unassigned')}</option>
                {people.map((p) => (
                  <option key={p.handle} value={p.handle}>
                    {p.display_name} (@{p.handle})
                  </option>
                ))}
              </Select>
            </Field>
          )}
        </S.Form>
      )}
      {preview && (
        <S.Summary>
          <p>
            {preview.dry_run
              ? t('bulk.previewSummary', { ok: preview.succeeded, failed: preview.failed })
              : t('bulk.doneSummary', { ok: preview.succeeded, failed: preview.failed })}
          </p>
          {preview.results
            .filter((r) => !r.ok)
            .map((r) => (
              <S.Failure key={r.key}>
                <strong>{r.key}</strong> {r.error}
              </S.Failure>
            ))}
        </S.Summary>
      )}
      {job && (
        <S.Summary>
          <p>{t('bulk.jobProgress', { done: job.progress, total: job.total })}</p>
          <S.Progress
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={job.total}
            aria-valuenow={job.progress}
          >
            <span style={{ width: `${(job.progress / Math.max(job.total, 1)) * 100}%` }} />
          </S.Progress>
        </S.Summary>
      )}
    </Modal>
  );
}
