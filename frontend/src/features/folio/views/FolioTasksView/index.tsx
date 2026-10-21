import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createLink } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { Tabs } from '../../../../components/ui/Tabs';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { formatDate } from '../../../../lib/format';
import {
  fetchMyTasks,
  setTaskDone,
  taskKeys,
  type FolioTask,
  type TaskStatus,
} from '../../../../services/api/folioWork';
import * as S from './style';

const BUCKETS = ['overdue', 'today', 'upcoming', 'no_date'] as const;
const PageLink = createLink(S.Page);

/** Mis tareas: action items assigned to you, grouped by when they're due. */
export function FolioTasksView() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [status, setStatus] = useState<TaskStatus>('open');
  const { data: tasks } = useQuery({
    queryKey: taskKeys.list(status),
    queryFn: () => fetchMyTasks(status),
  });
  const check = useMutation({
    mutationFn: ({ id, done }: { id: string; done: boolean }) => setTaskDone(id, done),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: taskKeys.all }),
    onError: (error) => toast(errorMessage(error), 'error'),
  });

  const row = (task: FolioTask) => (
    <S.Row key={task.id} $done={task.done}>
      <input
        type="checkbox"
        checked={task.done}
        aria-label={t('folio.tasks.check', { text: task.text })}
        onChange={(e) => check.mutate({ id: task.id, done: e.target.checked })}
      />
      <S.Text>{task.text}</S.Text>
      <PageLink to="/folio/p/$page" params={{ page: `${task.node.id}-${task.node.slug}` }}>
        {task.node.title}
      </PageLink>
      <S.Due $late={task.bucket === 'overdue' && !task.done}>
        {task.due ? formatDate(task.due) : t('folio.tasks.noDate')}
      </S.Due>
    </S.Row>
  );

  return (
    <>
      <PageTitle title={t('folio.tasks.title')} subtitle={t('folio.tasks.subtitle')} />
      <Tabs
        label={t('folio.tasks.filter')}
        value={status}
        onChange={setStatus}
        tabs={(['open', 'done', 'all'] as const).map((s) => ({
          id: s,
          label: t(`folio.tasks.status.${s}`),
        }))}
      />
      {tasks && tasks.length === 0 ? (
        <EmptyState plant="seed" title={t(`folio.tasks.empty.${status}`)} />
      ) : (
        <S.Groups>
          {BUCKETS.map((bucket) => {
            const group = (tasks ?? []).filter((task) => task.bucket === bucket);
            if (!group.length) return null;
            return (
              <S.Group key={bucket} aria-labelledby={`tasks-${bucket}`}>
                <h2 id={`tasks-${bucket}`}>
                  {t(`folio.tasks.buckets.${bucket}`)} <S.Count>{group.length}</S.Count>
                </h2>
                <ul>{group.map(row)}</ul>
              </S.Group>
            );
          })}
        </S.Groups>
      )}
    </>
  );
}
