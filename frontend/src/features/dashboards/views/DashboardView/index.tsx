import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from '@tanstack/react-router';
import { ArrowLeft } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import {
  dashboardKeys,
  deleteDashboard,
  fetchDashboard,
  patchDashboard,
} from '../../../../services/api/dashboards';
import { DashboardGrid } from '../../components/DashboardGrid';
import { DashboardHeader } from '../../components/DashboardHeader';
import { ShareModal } from '../../components/ShareModal';
import * as S from './style';

/** /d/{id}: one dashboard, with edit mode for whoever can change it. */
export function DashboardView() {
  const { t } = useTranslation();
  const { id } = useParams({ from: '/app/d/$id' });
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [editing, setEditing] = useState(false);
  const [catalog, setCatalog] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const { data, isPending, isError } = useQuery({
    queryKey: dashboardKeys.detail(id),
    queryFn: () => fetchDashboard(id),
  });
  const share = useMutation({
    mutationFn: (v: { visibility: 'private' | 'project' | 'instance'; project: string | null }) =>
      patchDashboard(id, v),
    onSuccess: () => {
      setSharing(false);
      void queryClient.invalidateQueries({ queryKey: ['dashboards'] });
    },
  });
  const remove = useMutation({
    mutationFn: () => deleteDashboard(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: dashboardKeys.list });
      void navigate({ to: '/dashboards' });
    },
  });

  if (isPending) return <PageSpinner />;
  if (isError || !data) return <EmptyState plant="seed" title={t('dashboards.notFound')} />;
  return (
    <S.Page>
      <Link to="/dashboards">
        <ArrowLeft size={14} />
        {t('dashboards.all')}
      </Link>
      <DashboardHeader
        dashboard={data}
        editing={editing}
        onEdit={setEditing}
        onAdd={() => setCatalog(true)}
        onShare={() => setSharing(true)}
        onDelete={() => setDeleting(true)}
      />
      <DashboardGrid
        dashboard={data}
        editing={editing}
        catalog={catalog}
        onCloseCatalog={() => setCatalog(false)}
      />
      {sharing && (
        <ShareModal
          dashboard={data}
          error={share.error ? errorMessage(share.error) : null}
          onCancel={() => {
            share.reset();
            setSharing(false);
          }}
          onSave={(visibility, project) => share.mutate({ visibility, project })}
        />
      )}
      <ConfirmDialog
        open={deleting}
        title={t('dashboards.delete', { name: data.name })}
        message={t('dashboards.deleteConfirm')}
        confirmLabel={t('common.delete')}
        onConfirm={() => remove.mutate()}
        onCancel={() => setDeleting(false)}
      />
    </S.Page>
  );
}
