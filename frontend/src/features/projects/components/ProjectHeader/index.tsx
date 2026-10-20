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
        <Tab to="/p/$key/summary" data-tour="project.tab.summary" params={params}>
          <LayoutDashboard />
          {t('nav.summary')}
        </Tab>
        <Tab
          to="/p/$key/board"
          data-tour="project.tab.board"
          params={params}
          search={{}}
          activeOptions={{ includeSearch: false }}
        >
          <Columns3 />
          {t('nav.board')}
        </Tab>
        <Tab
          to="/p/$key/backlog"
          data-tour="project.tab.backlog"
          params={params}
          search={{}}
          activeOptions={{ includeSearch: false }}
        >
          <ListTodo />
          {t('nav.backlog')}
        </Tab>
        <Tab
          to="/p/$key/inbox"
          data-tour="project.tab.inbox"
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
        <Tab
          to="/p/$key/list"
          data-tour="project.tab.list"
          params={params}
          search={{}}
          activeOptions={{ includeSearch: false }}
        >
          <List />
          {t('nav.list')}
        </Tab>
        <Tab
          to="/p/$key/timeline"
          data-tour="project.tab.timeline"
          params={params}
          search={{}}
          activeOptions={{ includeSearch: false }}
        >
          <CalendarRange />
          {t('nav.timeline')}
        </Tab>
        <Tab to="/p/$key/milestones" data-tour="project.tab.milestones" params={params}>
          <Flag />
          {t('nav.milestones')}
        </Tab>
        <Tab
          to="/p/$key/reports"
          data-tour="project.tab.reports"
          params={params}
          search={{}}
          activeOptions={{ includeSearch: false }}
        >
          <ChartLine />
          {t('nav.reports')}
        </Tab>
        <Tab
          to="/p/$key/settings"
          data-tour="project.tab.settings"
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
