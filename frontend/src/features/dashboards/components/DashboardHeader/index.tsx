import { useQueryClient } from '@tanstack/react-query';
import { Check, Pencil, Plus, RefreshCw, Share2, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import type { Dashboard } from '../../../../services/api/types';
import * as S from './style';

type Props = {
  dashboard: Dashboard;
  editing: boolean;
  showTitle?: boolean;
  onEdit: (editing: boolean) => void;
  onAdd: () => void;
  onShare?: () => void;
  onDelete?: () => void;
};

/** Name, sharing and the edit-mode toggle of a dashboard. */
export function DashboardHeader({
  dashboard,
  editing,
  showTitle = true,
  onEdit,
  onAdd,
  onShare,
  onDelete,
}: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  return (
    <S.Bar>
      {showTitle && <h1>{dashboard.name}</h1>}
      <Badge>{t(`dashboards.visibilities.${dashboard.visibility}`)}</Badge>
      {dashboard.project && !dashboard.is_project_default && <Badge>{dashboard.project}</Badge>}
      <S.Muted>{t('dashboards.byOwner', { owner: dashboard.owner })}</S.Muted>
      <S.Spacer />
      <Button
        size="sm"
        variant="ghost"
        onClick={() => void queryClient.invalidateQueries({ queryKey: ['tickets', 'widget'] })}
      >
        <RefreshCw />
        {t('dashboards.refresh')}
      </Button>
      {dashboard.can_edit && (
        <>
          {editing && (
            <Button size="sm" onClick={onAdd}>
              <Plus />
              {t('dashboards.addWidget')}
            </Button>
          )}
          {onShare && !dashboard.is_project_default && (
            <Button size="sm" onClick={onShare}>
              <Share2 />
              {t('dashboards.share')}
            </Button>
          )}
          {onDelete && !dashboard.is_project_default && (
            <Button size="sm" variant="ghost" onClick={onDelete}>
              <Trash2 />
              {t('common.delete')}
            </Button>
          )}
          <Button
            size="sm"
            variant={editing ? 'primary' : 'secondary'}
            onClick={() => onEdit(!editing)}
          >
            {editing ? <Check /> : <Pencil />}
            {editing ? t('dashboards.done') : t('dashboards.edit')}
          </Button>
        </>
      )}
    </S.Bar>
  );
}
