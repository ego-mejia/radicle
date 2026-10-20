import { useQuery } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useMe } from '../../../../hooks/useMe';
import { fetchProjects, projectKeys } from '../../../../services/api/projects';
import { CreateProjectModal } from '../../components/CreateProjectModal';
import { EditProjectModal } from '../../components/EditProjectModal';
import { ProjectCard } from '../../components/ProjectCard';
import * as S from './style';

export function ProjectsView() {
  const { t } = useTranslation();
  const me = useMe();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const { data: projects, isPending } = useQuery({
    queryKey: projectKeys.list(false),
    queryFn: () => fetchProjects(false),
  });
  const createButton = me.is_instance_admin && (
    <Button variant="primary" onClick={() => setCreating(true)} data-tour="projects.create">
      <Plus />
      {t('projects.create')}
    </Button>
  );

  return (
    <>
      <S.Head>
        <h1>{t('nav.projects')}</h1>
        {projects && projects.length > 0 && createButton}
      </S.Head>
      {isPending ? (
        <PageSpinner />
      ) : projects && projects.length > 0 ? (
        <S.Grid>
          {projects.map((project) => (
            <ProjectCard
              key={project.key}
              project={project}
              onEdit={
                me.is_instance_admin || project.role === 'admin'
                  ? () => setEditing(project.key)
                  : undefined
              }
            />
          ))}
        </S.Grid>
      ) : (
        <EmptyState
          plant="seed"
          title={t('projects.emptyTitle')}
          text={me.is_instance_admin ? t('projects.emptyAdmin') : t('projects.emptyMember')}
          action={createButton}
        />
      )}
      <CreateProjectModal open={creating} onOpenChange={setCreating} />
      {editing && <EditProjectModal projectKey={editing} onClose={() => setEditing(null)} />}
    </>
  );
}
