import { useMutation, useQueryClient } from '@tanstack/react-query';
import { MoreHorizontal, Plus } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../components/ui/Button';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { Menu } from '../../../../components/ui/Menu';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { patchMilestone, projectKeys } from '../../../../services/api/projects';
import type { Milestone } from '../../../../services/api/types';
import type { ProjectDetail } from '../../../../services/api/types';
import { MilestoneCard } from '../MilestoneCard';
import { MilestoneModal } from '../MilestoneModal';
import * as S from './style';

type Props = {
  project: ProjectDetail;
  renderHeader?: (addButton: React.ReactNode) => React.ReactNode;
};

/** Milestones of a project with create, edit, close and reopen for admins. */
export function MilestonesList({ project, renderHeader }: Props) {
  const { t } = useTranslation();
  const projectKey = project.key;
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [editing, setEditing] = useState<Milestone | 'new' | null>(null);
  const toggle = useMutation({
    mutationFn: (m: Milestone) =>
      patchMilestone(projectKey, m.name, { status: m.status === 'open' ? 'closed' : 'open' }),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: projectKeys.detail(projectKey) }),
    onError: (error) => toast(errorMessage(error), 'error'),
  });

  const isAdmin = project.role === 'admin' && !project.archived;
  const addButton = isAdmin && (
    <Button variant="primary" onClick={() => setEditing('new')}>
      <Plus />
      {t('milestones.create')}
    </Button>
  );

  return (
    <>
      {renderHeader?.(project.milestones.length > 0 && addButton)}
      {project.milestones.length === 0 ? (
        <EmptyState
          plant="sprout"
          title={t('milestones.emptyTitle')}
          text={t('milestones.emptyText')}
          action={addButton}
        />
      ) : (
        <S.List>
          {project.milestones.map((milestone) => (
            <MilestoneCard
              key={milestone.name}
              project={projectKey}
              milestone={milestone}
              actions={
                isAdmin && (
                  <Menu
                    align="end"
                    trigger={
                      <IconButton label={t('common.more')}>
                        <MoreHorizontal />
                      </IconButton>
                    }
                    items={[
                      {
                        key: 'edit',
                        label: t('common.edit'),
                        onSelect: () => setEditing(milestone),
                      },
                      {
                        key: 'toggle',
                        label:
                          milestone.status === 'open'
                            ? t('milestones.close')
                            : t('milestones.reopen'),
                        onSelect: () => toggle.mutate(milestone),
                      },
                    ]}
                  />
                )
              }
            />
          ))}
        </S.List>
      )}
      {editing && (
        <MilestoneModal
          project={projectKey}
          milestone={editing === 'new' ? undefined : editing}
          onClose={() => setEditing(null)}
        />
      )}
    </>
  );
}
