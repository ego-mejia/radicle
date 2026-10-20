import { useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { Tabs } from '../../../../components/ui/Tabs';
import { ProjectHeader } from '../../../projects/components/ProjectHeader';
import { useProject } from '../../../projects/hooks/useProject';
import { AreasSection } from '../../components/AreasSection';
import { CustomFieldsSection } from '../../components/CustomFieldsSection';
import { GeneralSection } from '../../components/GeneralSection';
import { GroupRolesSection } from '../../components/GroupRolesSection';
import { AuditLog } from '../../../audit/components/AuditLog';
import { InboxSettingsSection } from '../../components/InboxSettingsSection';
import { LevelsSection } from '../../components/LevelsSection';
import { MembersSection } from '../../components/MembersSection';
import { PermissionsSection } from '../../components/PermissionsSection';
import { ScreensSection } from '../../components/ScreensSection';
import { TemplateBanner } from '../../components/TemplateBanner';
import { WorkflowsSection } from '../../components/WorkflowsSection';
import { MilestonesList } from '../../../milestones/components/MilestonesList';
import { can } from '../../../../lib/permissions';
import * as S from './style';

type Tab =
  | 'general'
  | 'members'
  | 'permissions'
  | 'levels'
  | 'inbox'
  | 'audit'
  | 'areas'
  | 'milestones'
  | 'workflows'
  | 'fields'
  | 'screens';
const TABS: Tab[] = [
  'general',
  'members',
  'permissions',
  'levels',
  'inbox',
  'audit',
  'areas',
  'milestones',
  'workflows',
  'fields',
  'screens',
];

export function SettingsView() {
  const { t } = useTranslation();
  const { key } = useParams({ from: '/app/p/$key/settings' });
  const { tab } = useSearch({ from: '/app/p/$key/settings' });
  const navigate = useNavigate({ from: '/p/$key/settings' });
  const { data: project, isPending } = useProject(key.toUpperCase());
  const current = (TABS.includes(tab as Tab) ? tab : 'general') as Tab;

  if (isPending) return <PageSpinner />;
  if (!project) return <EmptyState plant="seed" title={t('board.notFound')} />;
  const isAdmin = can(project, 'project.settings');
  const manageMembers = can(project, 'members.manage');

  return (
    <>
      <ProjectHeader project={project} />
      <S.Stack>
        <TemplateBanner project={project} isAdmin={isAdmin} />
        <SettingsTabs
          current={current}
          onChange={(next) => void navigate({ search: { tab: next } })}
        />
        {current === 'general' && (
          <GeneralSection key={project.key} project={project} isAdmin={isAdmin} />
        )}
        {current === 'members' && (
          <>
            <MembersSection project={project} isAdmin={manageMembers} />
            <GroupRolesSection project={project} editable={manageMembers} />
          </>
        )}
        {current === 'audit' && <AuditLog project={project.key} />}
        {current === 'inbox' && (
          <InboxSettingsSection
            project={project}
            editable={project.role === 'admin' && !project.archived}
          />
        )}
        {current === 'levels' && (
          <LevelsSection
            project={project}
            editable={project.role === 'admin' && !project.archived}
          />
        )}
        {current === 'permissions' && (
          <PermissionsSection
            project={project}
            editable={project.role === 'admin' && !project.archived}
          />
        )}
        {current === 'areas' && <AreasSection project={project} isAdmin={isAdmin} />}
        {current === 'milestones' && (
          <MilestonesList project={project} renderHeader={(addButton) => addButton} />
        )}
        {current === 'workflows' && <WorkflowsSection project={project} isAdmin={isAdmin} />}
        {current === 'screens' && <ScreensSection project={project} isAdmin={isAdmin} />}
        {current === 'fields' && (
          <CustomFieldsSection
            project={project}
            isAdmin={isAdmin}
            locked={project.template?.mode === 'linked'}
          />
        )}
      </S.Stack>
    </>
  );
}

function SettingsTabs({ current, onChange }: { current: Tab; onChange: (tab: Tab) => void }) {
  const { t } = useTranslation();
  return (
    <Tabs
      label={t('nav.settings')}
      tour="settings.tab"
      value={current}
      onChange={onChange}
      tabs={TABS.map((id) => ({ id, label: t(`settings.${id}`) }))}
    />
  );
}
