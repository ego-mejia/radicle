import { useNavigate, useSearch } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { Tabs } from '../../../../components/ui/Tabs';
import { useMe } from '../../../../hooks/useMe';
import { AgentsTab } from '../../components/AgentsTab';
import { ProjectsTab } from '../../components/ProjectsTab';
import { UsersTab } from '../../components/UsersTab';
import * as S from './style';

type Tab = 'users' | 'agents' | 'projects';
const TABS: Tab[] = ['users', 'agents', 'projects'];

export function AdminView() {
  const { t } = useTranslation();
  const me = useMe();
  const { tab } = useSearch({ from: '/app/admin' });
  const navigate = useNavigate({ from: '/admin' });
  const current = (TABS.includes(tab as Tab) ? tab : 'users') as Tab;

  if (!me.is_instance_admin) return <EmptyState plant="seed" title={t('admin.forbidden')} />;

  return (
    <>
      <PageTitle title={t('nav.admin')} subtitle={t('admin.subtitle')} />
      <S.Stack>
        <Tabs
          label={t('nav.admin')}
          value={current}
          onChange={(next) => void navigate({ search: { tab: next } })}
          tabs={TABS.map((id) => ({ id, label: t(`admin.${id}`) }))}
        />
        {current === 'users' && <UsersTab />}
        {current === 'agents' && <AgentsTab />}
        {current === 'projects' && <ProjectsTab />}
      </S.Stack>
    </>
  );
}
