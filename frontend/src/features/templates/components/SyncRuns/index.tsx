import { useMutation, useQuery } from '@tanstack/react-query';
import { RotateCcw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { IconButton } from '../../../../components/ui/Button';
import { relativeTime } from '../../../../lib/format';
import { fetchSyncRuns, retrySyncRun, templateKeys } from '../../../../services/api/templates';
import type { SyncRun } from '../../../../services/api/types';
import * as S from './style';

const TONE = {
  pending: 'neutral',
  running: 'neutral',
  succeeded: 'accent',
  failed: 'danger',
} as const;

/** Propagation progress per linked project; refreshes while anything is in flight. */
export function SyncRuns({ templateId }: { templateId: string }) {
  const { t } = useTranslation();
  const { data: runs = [], refetch } = useQuery({
    queryKey: templateKeys.runs(templateId),
    queryFn: () => fetchSyncRuns(templateId),
    refetchInterval: (query) =>
      (query.state.data ?? []).some(
        (r: SyncRun) => r.status === 'pending' || r.status === 'running',
      )
        ? 1500
        : false,
  });
  const retry = useMutation({
    mutationFn: (runId: string) => retrySyncRun(templateId, runId),
    onSuccess: () => void refetch(),
  });
  if (!runs.length) return <S.Muted>{t('templates.noRuns')}</S.Muted>;
  return (
    <S.Table>
      <thead>
        <tr>
          <th>{t('templates.project')}</th>
          <th>{t('templates.version')}</th>
          <th>{t('templates.status')}</th>
          <th>{t('templates.when')}</th>
          <th aria-label={t('templates.retry')} />
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <tr key={run.id}>
            <td>{run.project}</td>
            <td>v{run.template_version}</td>
            <td>
              <Badge tone={TONE[run.status]}>{t(`templates.runStatus.${run.status}`)}</Badge>
              {run.error && <S.Error>{run.error}</S.Error>}
            </td>
            <td>{relativeTime(run.finished_at ?? run.created_at)}</td>
            <td>
              {run.status === 'failed' && (
                <IconButton label={t('templates.retry')} onClick={() => retry.mutate(run.id)}>
                  <RotateCcw />
                </IconButton>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </S.Table>
  );
}
