import { useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { Tabs } from '../../../../components/ui/Tabs';
import { ProjectHeader } from '../../../projects/components/ProjectHeader';
import { useProject } from '../../../projects/hooks/useProject';
import { AreasSection } from '../../components/AreasSection';
import { GeneralSection } from '../../components/GeneralSection';
import { MembersSection } from '../../components/MembersSection';
import { WorkflowsSection } from '../../components/WorkflowsSection';
import { MilestonesList } from '../../../milestones/components/MilestonesList';
import * as S from './style';

type Tab = 'general' | 'members' | 'areas' | 'milestones' | 'workflows';
const TABS: Tab[] = ['general', 'members', 'areas', 'milestones', 'workflows'];

export function SettingsView() {
  const { t } = useTranslation();
  const { key } = useParams({ from: '/app/p/$key/settings' });
  const { tab } = useSearch({ from: '/app/p/$key/settings' });
  const navigate = useNavigate({ from: '/p/$key/settings' });
  const { data: project, isPending } = useProject(key.toUpperCase());
  const current = (TABS.includes(tab as Tab) ? tab : 'general') as Tab;

  if (isPending) return <PageSpinner />;
  if (!project) return <EmptyState plant="seed" title={t('board.notFound')} />;
  const isAdmin = project.role === 'admin';

  return (
    <>
      <ProjectHeader project={project} />
      <S.Stack>
        <SettingsTabs
          current={current}
          onChange={(next) => void navigate({ search: { tab: next } })}
        />
        {current === 'general' && (
          <GeneralSection key={project.key} project={project} isAdmin={isAdmin} />
        )}
        {current === 'members' && <MembersSection project={project} isAdmin={isAdmin} />}
        {current === 'areas' && <AreasSection project={project} isAdmin={isAdmin} />}
        {current === 'milestones' && (
          <MilestonesList project={project} renderHeader={(addButton) => addButton} />
        )}
        {current === 'workflows' && <WorkflowsSection project={project} />}
      </S.Stack>
    </>
  );
}

function SettingsTabs({ current, onChange }: { current: Tab; onChange: (tab: Tab) => void }) {
  const { t } = useTranslation();
  return (
    <Tabs
      label={t('nav.settings')}
      value={current}
      onChange={onChange}
      tabs={TABS.map((id) => ({ id, label: t(`settings.${id}`) }))}
    />
  );
}
