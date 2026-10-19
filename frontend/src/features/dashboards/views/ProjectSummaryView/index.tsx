import { useQuery } from '@tanstack/react-query';
import { useParams } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { dashboardKeys, fetchProjectDashboard } from '../../../../services/api/dashboards';
import { ProjectHeader } from '../../../projects/components/ProjectHeader';
import { useProject } from '../../../projects/hooks/useProject';
import { DashboardGrid } from '../../components/DashboardGrid';
import { DashboardHeader } from '../../components/DashboardHeader';

/** The project's "Summary" dashboard, as a project tab; its admins edit it. */
export function ProjectSummaryView() {
  const { t } = useTranslation();
  const { key } = useParams({ from: '/app/p/$key/summary' });
  const projectKey = key.toUpperCase();
  const [editing, setEditing] = useState(false);
  const [catalog, setCatalog] = useState(false);
  const { data: project, isPending: loadingProject, isError } = useProject(projectKey);
  const { data } = useQuery({
    queryKey: dashboardKeys.project(projectKey),
    queryFn: () => fetchProjectDashboard(projectKey),
  });
  if (loadingProject) return <PageSpinner />;
  if (isError || !project) return <EmptyState plant="seed" title={t('board.notFound')} />;
  return (
    <>
      <ProjectHeader project={project} />
      {!data ? (
        <PageSpinner />
      ) : (
        <>
          <DashboardHeader
            dashboard={data}
            editing={editing}
            showTitle={false}
            onEdit={setEditing}
            onAdd={() => setCatalog(true)}
          />
          <DashboardGrid
            dashboard={data}
            editing={editing}
            catalog={catalog}
            onCloseCatalog={() => setCatalog(false)}
          />
        </>
      )}
    </>
  );
}
