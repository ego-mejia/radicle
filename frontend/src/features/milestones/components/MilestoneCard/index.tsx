import { Link } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../components/icons/CategoryIcon';
import { MarkdownView } from '../../../../components/Markdown/MarkdownView';
import { Badge } from '../../../../components/ui/Badge';
import { formatDate, isOverdue } from '../../../../lib/format';
import { rqlValue } from '../../../../lib/rql';
import { CATEGORIES, type Milestone } from '../../../../services/api/types';
import * as S from './style';

type Props = { project: string; milestone: Milestone; actions?: React.ReactNode };

/** Milestone with target date and a progress bar split by status category. */
export function MilestoneCard({ project, milestone, actions }: Props) {
  const { t } = useTranslation();
  const counts = milestone.counts;
  const total = counts.todo + counts.in_progress + counts.done;
  const percent = total ? Math.round((counts.done / total) * 100) : 0;
  const closed = milestone.status === 'closed';
  const late = !closed && isOverdue(milestone.target_date) && counts.done < total;
  return (
    <S.Card $closed={closed}>
      <S.Top>
        <h2>{milestone.name}</h2>
        {closed && <Badge>{t('milestones.closed')}</Badge>}
        <S.Spacer />
        {milestone.target_date && (
          <S.Date $late={late}>
            {t('milestones.target', { date: formatDate(milestone.target_date) })}
          </S.Date>
        )}
        {actions}
      </S.Top>
      {milestone.description_md && (
        <S.Description>
          <MarkdownView readOnly>{milestone.description_md}</MarkdownView>
        </S.Description>
      )}
      <S.Bar
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={milestone.name}
      >
        {CATEGORIES.slice()
          .reverse()
          .map((category) => (
            <S.Segment
              key={category}
              $category={category}
              $share={total ? counts[category] / total : 0}
            />
          ))}
      </S.Bar>
      <S.Legend>
        {CATEGORIES.map((category) => (
          <span key={category}>
            <CategoryIcon category={category} />
            {t(`ticket.categories.${category}`)}: {counts[category]}
          </span>
        ))}
        <span>{t('milestones.percent', { percent })}</span>
        <Link
          to="/p/$key/list"
          params={{ key: project }}
          search={{
            q: `project = ${project} AND milestone = ${rqlValue(milestone.name)} ORDER BY status`,
          }}
        >
          {t('milestones.seeTickets')}
        </Link>
      </S.Legend>
    </S.Card>
  );
}
