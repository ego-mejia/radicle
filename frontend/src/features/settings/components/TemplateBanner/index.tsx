import { Link } from '@tanstack/react-router';
import { Unlink } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { detachProject } from '../../../../services/api/templates';
import type { ProjectDetail } from '../../../../services/api/types';
import { useSettingsMutation } from '../../hooks/useSettingsMutation';
import * as S from './style';

/** "Linked to <template> v3" with a Detach button, or "independent" once detached. */
export function TemplateBanner({ project, isAdmin }: { project: ProjectDetail; isAdmin: boolean }) {
  const { t } = useTranslation();
  const [confirm, setConfirm] = useState(false);
  const detach = useSettingsMutation(
    project.key,
    () => detachProject(project.key),
    () => setConfirm(false),
  );
  const template = project.template;
  if (!template) return null;
  const linked = template.mode === 'linked';
  const name = (
    <Link to="/admin/templates/$id" params={{ id: template.id }} search={{}}>
      {template.name}
    </Link>
  );
  return (
    <S.Banner $linked={linked} role="status">
      <S.Text>
        {linked ? (
          <>
            {t('templates.bannerLinked')} {name} v{template.applied_version ?? '?'}
            {template.applied_version !== template.version && (
              <S.Muted> · {t('templates.syncing', { version: template.version })}</S.Muted>
            )}
            <S.Muted>{t('templates.bannerLinkedHelp')}</S.Muted>
          </>
        ) : (
          <>
            {t('templates.bannerDetached')} {name}.
            <S.Muted>{t('templates.bannerDetachedHelp')}</S.Muted>
          </>
        )}
      </S.Text>
      {linked && isAdmin && !project.archived && (
        <Button size="sm" onClick={() => setConfirm(true)}>
          <Unlink />
          {t('templates.detach')}
        </Button>
      )}
      <ConfirmDialog
        open={confirm}
        title={t('templates.detachTitle', { key: project.key })}
        message={t('templates.detachMessage', { template: template.name })}
        confirmLabel={t('templates.detach')}
        onConfirm={() => detach.mutate(undefined)}
        onCancel={() => setConfirm(false)}
      />
    </S.Banner>
  );
}
