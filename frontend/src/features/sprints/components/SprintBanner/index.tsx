import { Link } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { formatHours } from '../../../../lib/duration';
import { formatDate } from '../../../../lib/format';
import { isoPlus, sprintDays } from '../../../../lib/sprints';
import type { Sprint } from '../../../../services/api/types';
import * as S from './style';

type Props = { project: string; boardId: string; sprint: Sprint | null | undefined };

/** On a Scrum board: the active sprint with its goal and days left, or how to start one. */
export function SprintBanner({ project, boardId, sprint }: Props) {
  const { t } = useTranslation();
  const backlog = (
    <Link to="/p/$key/backlog" params={{ key: project }} search={{ board: boardId }}>
      {t('sprints.goBacklog')}
    </Link>
  );
  if (!sprint) {
    return (
      <S.Banner role="status">
        <strong>{t('sprints.noActive')}</strong>
        <span>{t('sprints.noActiveHelp')}</span>
        {backlog}
      </S.Banner>
    );
  }
  const left = sprint.end_date ? Math.max(0, sprintDays(isoPlus(0), sprint.end_date)) : null;
  return (
    <S.Banner aria-label={sprint.name}>
      <strong>{sprint.name}</strong>
      {sprint.start_date && (
        <span>
          {formatDate(sprint.start_date)} – {formatDate(sprint.end_date)}
        </span>
      )}
      {left != null && <span>{t('sprints.daysLeft', { count: left })}</span>}
      <span>
        {sprint.done_count}/{sprint.ticket_count} · {formatHours(sprint.remaining_hours)}
      </span>
      {sprint.goal && <S.Goal>{sprint.goal}</S.Goal>}
      {backlog}
    </S.Banner>
  );
}
