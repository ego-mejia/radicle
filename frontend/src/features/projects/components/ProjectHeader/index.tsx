import { useQuery } from '@tanstack/react-query';
import { createLink } from '@tanstack/react-router';
import {
  CalendarRange,
  ChartLine,
  Columns3,
  Flag,
  Inbox,
  LayoutDashboard,
  List,
  ListTodo,
  Settings,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge, TicketKey } from '../../../../components/ui/Badge';
import { fetchInbox, inboxKeys } from '../../../../services/api/inbox';
import type { ProjectDetail } from '../../../../services/api/types';
import * as S from './style';

const Tab = createLink(S.Tab);

type Props = { project: ProjectDetail; actions?: React.ReactNode };

export function ProjectHeader({ project, actions }: Props) {
  const { t } = useTranslation();
  const params = { key: project.key };
  const { data: inbox } = useQuery({
    queryKey: inboxKeys.list(project.key, { tab: 'new' }),
    queryFn: () => fetchInbox(project.key, { tab: 'new' }),
    staleTime: 60_000,
  });
  const newItems = inbox?.counts.new ?? 0;
  return (
    <S.Header>
      <S.TitleRow>
        <TicketKey>{project.key}</TicketKey>
        <h1>{project.name}</h1>
        {project.archived && <Badge tone="warning">{t('projects.archived')}</Badge>}
        <S.Spacer />
        {actions}
      </S.TitleRow>
      <S.Tabs aria-label={project.name}>
        <Tab to="/p/$key/summary" params={params}>
          <LayoutDashboard />
          {t('nav.summary')}
        </Tab>
        <Tab
          to="/p/$key/board"
          params={params}
          search={{}}
          activeOptions={{ includeSearch: false }}
        >
          <Columns3 />
          {t('nav.board')}
        </Tab>
        <Tab
          to="/p/$key/backlog"
          params={params}
          search={{}}
          activeOptions={{ includeSearch: false }}
        >
          <ListTodo />
          {t('nav.backlog')}
        </Tab>
        <Tab
          to="/p/$key/inbox"
          params={params}
          search={{}}
          activeOptions={{ includeSearch: false }}
        >
          <Inbox />
          {t('nav.inbox')}
          {newItems > 0 && (
            <S.Count aria-label={t('inbox.newCount', { count: newItems })}>{newItems}</S.Count>
          )}
        </Tab>
        <Tab to="/p/$key/list" params={params} search={{}} activeOptions={{ includeSearch: false }}>
          <List />
          {t('nav.list')}
        </Tab>
        <Tab
          to="/p/$key/timeline"
          params={params}
          search={{}}
          activeOptions={{ includeSearch: false }}
        >
          <CalendarRange />
          {t('nav.timeline')}
        </Tab>
        <Tab to="/p/$key/milestones" params={params}>
          <Flag />
          {t('nav.milestones')}
        </Tab>
        <Tab
          to="/p/$key/reports"
          params={params}
          search={{}}
          activeOptions={{ includeSearch: false }}
        >
          <ChartLine />
          {t('nav.reports')}
        </Tab>
        <Tab
          to="/p/$key/settings"
          params={params}
          search={{}}
          activeOptions={{ includeSearch: false }}
        >
          <Settings />
          {t('nav.settings')}
        </Tab>
      </S.Tabs>
    </S.Header>
  );
}
