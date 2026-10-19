import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from '@tanstack/react-router';
import { LayoutDashboard } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { Input } from '../../../../components/ui/Input';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { relativeTime } from '../../../../lib/format';
import {
  createDashboard,
  dashboardKeys,
  fetchDashboards,
} from '../../../../services/api/dashboards';
import * as S from './style';

/** /dashboards: the ones you can see, and a new one. */
export function DashboardsView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [name, setName] = useState('');
  const { data, isPending } = useQuery({ queryKey: dashboardKeys.list, queryFn: fetchDashboards });
  const create = useMutation({
    mutationFn: () => createDashboard({ name }),
    onSuccess: (d) => {
      void queryClient.invalidateQueries({ queryKey: dashboardKeys.list });
      void navigate({ to: '/d/$id', params: { id: d.id } });
    },
  });
  return (
    <S.Page>
      <PageTitle title={t('dashboards.title')} />
      <S.Create
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim()) create.mutate();
        }}
      >
        <Input
          aria-label={t('dashboards.newName')}
          placeholder={t('dashboards.newName')}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Button type="submit" variant="primary" disabled={!name.trim() || create.isPending}>
          {t('dashboards.create')}
        </Button>
        {create.error && <S.Error role="alert">{errorMessage(create.error)}</S.Error>}
      </S.Create>
      {isPending ? (
        <PageSpinner />
      ) : !data?.length ? (
        <EmptyState plant="pot" title={t('dashboards.none')} />
      ) : (
        <S.Grid>
          {data.map((d) => (
            <Link
              key={d.id}
              to={d.is_project_default && d.project ? '/p/$key/summary' : '/d/$id'}
              params={{ id: d.id, key: d.project ?? '' }}
            >
              <LayoutDashboard />
              <strong>{d.is_project_default ? `${d.project} · ${d.name}` : d.name}</strong>
              <span>
                <Badge>{t(`dashboards.visibilities.${d.visibility}`)}</Badge>
                {t('dashboards.byOwner', { owner: d.owner })} · {relativeTime(d.updated_at)}
              </span>
            </Link>
          ))}
        </S.Grid>
      )}
    </S.Page>
  );
}
