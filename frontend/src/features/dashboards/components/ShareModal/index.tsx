import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Select } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useMe } from '../../../../hooks/useMe';
import type { DashboardSummary } from '../../../../services/api/types';

type Visibility = DashboardSummary['visibility'];

type Props = {
  dashboard: DashboardSummary;
  error?: string | null;
  onCancel: () => void;
  onSave: (visibility: Visibility, project: string | null) => void;
};

/** Who sees the dashboard: only you, a project, or the whole instance. */
export function ShareModal({ dashboard, error, onCancel, onSave }: Props) {
  const { t } = useTranslation();
  const me = useMe();
  const [visibility, setVisibility] = useState<Visibility>(dashboard.visibility);
  const [project, setProject] = useState(dashboard.project ?? me.projects?.[0]?.key ?? '');
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onCancel()}
      title={t('dashboards.share')}
      footer={
        <>
          <Button onClick={onCancel}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            onClick={() => onSave(visibility, visibility === 'project' ? project : null)}
          >
            {t('common.save')}
          </Button>
        </>
      }
    >
      <Field label={t('dashboards.visibility')} hint={t(`dashboards.visibilityHelp.${visibility}`)}>
        <Select value={visibility} onChange={(e) => setVisibility(e.target.value as Visibility)}>
          <option value="private">{t('dashboards.visibilities.private')}</option>
          <option value="project">{t('dashboards.visibilities.project')}</option>
          {me.is_instance_admin && (
            <option value="instance">{t('dashboards.visibilities.instance')}</option>
          )}
        </Select>
      </Field>
      {visibility === 'project' && (
        <Field label={t('dashboards.project')}>
          <Select value={project} onChange={(e) => setProject(e.target.value)}>
            {(me.projects ?? []).map((p) => (
              <option key={p.key} value={p.key}>
                {p.key} · {p.name}
              </option>
            ))}
          </Select>
        </Field>
      )}
      <FormError>{error}</FormError>
    </Modal>
  );
}
