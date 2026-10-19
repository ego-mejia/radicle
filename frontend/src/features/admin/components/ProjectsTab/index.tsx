import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { Plus } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge, TicketKey } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { SettingsCard, SettingsParts as S } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { fetchProjects, projectKeys, setArchived } from '../../../../services/api/projects';
import { CreateProjectModal } from '../../../projects/components/CreateProjectModal';

export function ProjectsTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [creating, setCreating] = useState(false);
  const { data: projects, isPending } = useQuery({
    queryKey: projectKeys.list(true),
    queryFn: () => fetchProjects(true),
  });
  const archive = useMutation({
    mutationFn: (v: { key: string; archived: boolean }) => setArchived(v.key, v.archived),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: projectKeys.all }),
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  if (isPending) return <PageSpinner />;
  return (
    <SettingsCard title={t('nav.projects')}>
      <S.Rows>
        {(projects ?? []).map((p) => (
          <S.Row key={p.key}>
            <S.Grow>
              <TicketKey>{p.key}</TicketKey>
              <Link to="/p/$key/board" params={{ key: p.key }} search={{}}>
                {p.name}
              </Link>
              <small>{t('projects.openTickets', { count: p.open_tickets })}</small>
              {p.archived && <Badge tone="warning">{t('projects.archived')}</Badge>}
            </S.Grow>
            <Button
              size="sm"
              variant={p.archived ? 'secondary' : 'danger'}
              onClick={() => archive.mutate({ key: p.key, archived: !p.archived })}
            >
              {p.archived ? t('settings.unarchive') : t('settings.archive')}
            </Button>
          </S.Row>
        ))}
      </S.Rows>
      <S.Actions>
        <Button variant="primary" onClick={() => setCreating(true)}>
          <Plus />
          {t('projects.create')}
        </Button>
      </S.Actions>
      <CreateProjectModal open={creating} onOpenChange={setCreating} />
    </SettingsCard>
  );
}
