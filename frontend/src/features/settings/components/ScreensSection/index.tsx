import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { SettingsCard, SettingsParts as S } from '../../../../components/ui/SettingsCard';
import { useToast } from '../../../../hooks/useToast';
import { toConf } from '../../../../lib/workflow';
import { fetchScreens, putScreens, screenKeys } from '../../../../services/api/screens';
import type { ProjectDetail, ScreenIn } from '../../../../services/api/types';
import { type ScreenConf, ScreensEditor } from '../../../templates/components/ScreensEditor';
import { useSettingsMutation } from '../../hooks/useSettingsMutation';

type Props = { project: ProjectDetail; isAdmin: boolean };

/** Screens of the project; editable only when it is independent from its template. */
export function ScreensSection({ project, isAdmin }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const linked = project.template?.mode === 'linked';
  const editable = isAdmin && !linked && !project.archived;
  const { data: saved = [], refetch } = useQuery({
    queryKey: screenKeys.list(project.key),
    queryFn: () => fetchScreens(project.key),
  });
  const original: ScreenConf[] = saved.map((s) => ({
    type: s.type,
    operation: s.operation,
    transition: s.transition,
    fields: s.fields,
  }));
  const [draft, setDraft] = useState<ScreenConf[] | null>(null);
  const value = draft ?? original;
  const save = useSettingsMutation(
    project.key,
    () => putScreens(project.key, value as ScreenIn[]),
    () => {
      setDraft(null);
      void refetch();
      toast(t('profile.saved'));
    },
  );
  const workflows = Object.fromEntries(project.workflows.map((w) => [w.type, toConf(w)]));
  return (
    <SettingsCard
      title={t('screens.title')}
      help={
        linked ? t('screens.linkedHelp', { template: project.template?.name ?? '' }) : undefined
      }
    >
      <ScreensEditor
        screens={value}
        workflows={workflows}
        customFields={project.custom_fields.map((f) => ({
          key: f.key,
          name: f.name,
          types: f.applies_to_types,
        }))}
        readOnly={!editable}
        onChange={setDraft}
      />
      {editable && (
        <S.Actions>
          <Button disabled={!draft} onClick={() => setDraft(null)}>
            {t('templates.discard')}
          </Button>
          <Button
            variant="primary"
            disabled={!draft || save.isPending}
            onClick={() => save.mutate(undefined)}
          >
            {t('common.save')}
          </Button>
        </S.Actions>
      )}
    </SettingsCard>
  );
}
