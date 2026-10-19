import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input, Textarea } from '../../../../components/ui/Input';
import { Select } from '../../../../components/ui/Input';
import { patchProject, setArchived } from '../../../../services/api/projects';
import { putProjectSettings } from '../../../../services/api/templates';
import type { BlockedPolicy, ProjectDetail } from '../../../../services/api/types';
import { SaveAsTemplate } from '../SaveAsTemplate';
import { useSettingsMutation } from '../../hooks/useSettingsMutation';
import { SettingsCard, SettingsParts as S } from '../../../../components/ui/SettingsCard';

export function GeneralSection({ project, isAdmin }: { project: ProjectDetail; isAdmin: boolean }) {
  const { t } = useTranslation();
  const [name, setName] = useState(project.name);
  const [description, setDescription] = useState(project.description_md);
  const save = useSettingsMutation(project.key, () =>
    patchProject(project.key, { name, description_md: description }),
  );
  const archive = useSettingsMutation(project.key, (archived: boolean) =>
    setArchived(project.key, archived),
  );
  const editable = isAdmin && !project.archived;
  const policy = useSettingsMutation(project.key, (value: BlockedPolicy) =>
    putProjectSettings(project.key, value),
  );
  const linked = project.template?.mode === 'linked';

  return (
    <SettingsCard title={t('settings.general')}>
      <Field label={t('projects.name')}>
        <Input value={name} onChange={(e) => setName(e.target.value)} disabled={!editable} />
      </Field>
      <Field label={t('projects.key')} hint={t('settings.keyFixed')}>
        <Input value={project.key} disabled />
      </Field>
      <Field label={t('projects.description')}>
        <Textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={!editable}
        />
      </Field>
      <Field
        label={t('templates.blockedPolicy')}
        hint={linked ? t('templates.policyFromTemplate') : t('templates.blockedPolicyHint')}
      >
        <Select
          value={project.blocked_policy}
          disabled={!editable || linked}
          onChange={(e) => policy.mutate(e.target.value as BlockedPolicy)}
        >
          <option value="warn">{t('templates.policy.warn')}</option>
          <option value="enforce">{t('templates.policy.enforce')}</option>
        </Select>
      </Field>
      {isAdmin && (
        <S.Actions>
          {editable && (
            <Button
              variant="primary"
              onClick={() => save.mutate(undefined)}
              disabled={save.isPending}
            >
              {t('common.save')}
            </Button>
          )}
          <Button
            variant={project.archived ? 'secondary' : 'danger'}
            onClick={() => archive.mutate(!project.archived)}
          >
            {project.archived ? t('settings.unarchive') : t('settings.archive')}
          </Button>
          <SaveAsTemplate project={project} />
        </S.Actions>
      )}
    </SettingsCard>
  );
}
