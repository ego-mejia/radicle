import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../components/icons/CategoryIcon';
import { TypeIcon } from '../../../../components/icons/TypeIcon';
import { Badge } from '../../../../components/ui/Badge';
import type { ProjectDetail } from '../../../../services/api/types';
import { SettingsCard } from '../../../../components/ui/SettingsCard';
import { WorkflowForm } from './components/WorkflowForm';
import * as S from './style';

type Props = { project: ProjectDetail; isAdmin: boolean };

/** Editable in independent projects; linked projects show their template's workflows. */
export function WorkflowsSection({ project, isAdmin }: Props) {
  const { t } = useTranslation();
  const editable = isAdmin && !project.archived && project.template?.mode !== 'linked';
  if (editable) {
    return (
      <SettingsCard title={t('settings.workflows')} help={t('settings.workflowsEditHelp')}>
        <WorkflowForm project={project} />
      </SettingsCard>
    );
  }
  return (
    <SettingsCard
      title={t('settings.workflows')}
      help={
        project.template?.mode === 'linked'
          ? t('settings.workflowsLinkedHelp', { template: project.template.name })
          : t('settings.workflowsHelp')
      }
    >
      <S.Grid>
        {project.workflows.map((wf) => (
          <S.Workflow key={wf.type}>
            <h3>
              <TypeIcon type={wf.type} />
              {t(`ticket.types.${wf.type}`)}
            </h3>
            <S.Statuses>
              {wf.statuses.map((s) => (
                <Badge key={s.name} tone={s.category === 'done' ? 'accent' : 'neutral'}>
                  <CategoryIcon category={s.category} size={12} />
                  {s.name}
                </Badge>
              ))}
            </S.Statuses>
            <S.Table>
              <tbody>
                {wf.transitions.map((tr) => (
                  <tr key={`${tr.name}-${tr.from_status ?? 'any'}`}>
                    <td>{tr.name}</td>
                    <td>
                      {tr.from_status ?? t('settings.anyStatus')} → {tr.to_status}
                      {tr.allowed_resolutions &&
                        ` (${tr.allowed_resolutions.map((r) => t(`ticket.resolutions.${r}`)).join(', ')})`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </S.Table>
          </S.Workflow>
        ))}
      </S.Grid>
    </SettingsCard>
  );
}
