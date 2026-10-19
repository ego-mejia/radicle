import { useTranslation } from 'react-i18next';
import { CategoryIcon } from '../../../../components/icons/CategoryIcon';
import { TypeIcon } from '../../../../components/icons/TypeIcon';
import { Badge } from '../../../../components/ui/Badge';
import type { ProjectDetail } from '../../../../services/api/types';
import { SettingsCard } from '../../../../components/ui/SettingsCard';
import * as S from './style';

/** Read-only in stage 1; editing workflows arrives with templates. */
export function WorkflowsSection({ project }: { project: ProjectDetail }) {
  const { t } = useTranslation();
  return (
    <SettingsCard title={t('settings.workflows')} help={t('settings.workflowsHelp')}>
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
