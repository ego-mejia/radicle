import { useParams } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { ProjectHeader } from '../../../projects/components/ProjectHeader';
import { useProject } from '../../../projects/hooks/useProject';
import { MilestonesList } from '../../components/MilestonesList';

export function MilestonesView() {
  const { t } = useTranslation();
  const { key } = useParams({ from: '/app/p/$key/milestones' });
  const { data: project, isPending } = useProject(key.toUpperCase());
  if (isPending) return <PageSpinner />;
  if (!project) return <EmptyState plant="seed" title={t('board.notFound')} />;
  return (
    <MilestonesList
      project={project}
      renderHeader={(addButton) => <ProjectHeader project={project} actions={addButton} />}
    />
  );
}
