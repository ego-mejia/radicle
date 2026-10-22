import type { QueryClient } from '@tanstack/react-query';
import { createRoute, createRouter, redirect } from '@tanstack/react-router';
import { AdminView } from './features/admin/views/AdminView';
import { LinkChatView } from './features/integrations/views/LinkChatView';
import { LoginView } from './features/auth/views/LoginView';
import { SetupView } from './features/auth/views/SetupView';
import { BoardSettingsView } from './features/board/views/BoardSettingsView';
import { BoardView } from './features/board/views/BoardView';
import { BacklogView } from './features/sprints/views/BacklogView';
import { TimelineView } from './features/timeline/views/TimelineView';
import { ReportsView } from './features/reports/views/ReportsView';
import { InboxView } from './features/inbox/views/InboxView';
import { DashboardsView } from './features/dashboards/views/DashboardsView';
import { DashboardView } from './features/dashboards/views/DashboardView';
import { ProjectSummaryView } from './features/dashboards/views/ProjectSummaryView';
import { ListView } from './features/list/views/ListView';
import { MilestonesView } from './features/milestones/views/MilestonesView';
import { MyTicketsView } from './features/mytickets/views/MyTicketsView';
import { ProfileView } from './features/profile/views/ProfileView';
import { ProjectsView } from './features/projects/views/ProjectsView';
import { SettingsView } from './features/settings/views/SettingsView';
import { TemplateEditorView } from './features/templates/views/TemplateEditorView';
import { TicketPageView } from './features/tickets/views/TicketPageView';
import { FolioPrintView } from './features/folio/views/FolioPrintView';
import { FolioPublicView } from './features/folio/views/FolioPublicView';
import { AppPage } from './pages/AppPage';
import { AuthPage } from './pages/AuthPage';
import { authKeys, fetchMe, fetchSetupStatus } from './services/api/auth';
import { isApiError } from './services/api/client';
import { folioRouteTree } from './features/folio/routes';
import { rootRoute, str } from './routerRoot';

export type { FolioSearchParams } from './features/folio/routes';

export type BoardSearch = {
  type?: string;
  area?: string;
  milestone?: string;
  assignee?: string;
  tag?: string;
  t?: string;
  board?: string;
  qf?: string;
  lane?: string;
};

async function needsSetup(queryClient: QueryClient): Promise<boolean> {
  const status = await queryClient.fetchQuery({
    queryKey: authKeys.setup,
    queryFn: fetchSetupStatus,
    staleTime: 0,
  });
  return status.needs_setup;
}

const authLayout = createRoute({
  getParentRoute: () => rootRoute,
  id: 'auth',
  component: AuthPage,
});

const setupRoute = createRoute({
  getParentRoute: () => authLayout,
  path: '/setup',
  component: SetupView,
  beforeLoad: async ({ context }) => {
    if (!(await needsSetup(context.queryClient))) throw redirect({ to: '/login' });
  },
});

const loginRoute = createRoute({
  getParentRoute: () => authLayout,
  path: '/login',
  component: LoginView,
  validateSearch: (search: Record<string, unknown>): { next?: string; sso_error?: string } => ({
    next: str(search.next),
    sso_error: str(search.sso_error),
  }),
  beforeLoad: async ({ context }) => {
    if (await needsSetup(context.queryClient)) throw redirect({ to: '/setup' });
  },
});

const appLayout = createRoute({
  getParentRoute: () => rootRoute,
  id: 'app',
  component: AppPage,
  beforeLoad: async ({ context, location }) => {
    try {
      await context.queryClient.ensureQueryData({ queryKey: authKeys.me, queryFn: fetchMe });
    } catch (error) {
      if (!isApiError(error, 401)) throw error;
      if (await needsSetup(context.queryClient)) throw redirect({ to: '/setup' });
      throw redirect({ to: '/login', search: { next: location.href } });
    }
  },
});

const boardSearch = (search: Record<string, unknown>): BoardSearch => ({
  type: str(search.type),
  area: str(search.area),
  milestone: str(search.milestone),
  assignee: str(search.assignee),
  tag: str(search.tag),
  t: str(search.t),
  board: str(search.board),
  qf: str(search.qf),
  lane: str(search.lane),
});

const projectsRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/',
  component: ProjectsView,
});

const boardRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/p/$key/board',
  component: BoardView,
  validateSearch: boardSearch,
});

const boardSettingsRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/p/$key/boards/$id',
  component: BoardSettingsView,
});

const backlogRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/p/$key/backlog',
  component: BacklogView,
  validateSearch: (search: Record<string, unknown>): { board?: string; t?: string } => ({
    board: str(search.board),
    t: str(search.t),
  }),
});

const timelineRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/p/$key/timeline',
  component: TimelineView,
  validateSearch: (
    search: Record<string, unknown>,
  ): { q?: string; group?: string; zoom?: string; t?: string } => ({
    q: str(search.q),
    group: str(search.group),
    zoom: str(search.zoom),
    t: str(search.t),
  }),
});

type ReportSearch = {
  type?: string;
  board?: string;
  sprint?: string;
  milestone?: string;
  area?: string;
  from?: string;
  to?: string;
  field?: string;
  interval?: string;
  by?: string;
};

const reportsRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/p/$key/reports',
  component: ReportsView,
  validateSearch: (search: Record<string, unknown>): ReportSearch => ({
    type: str(search.type),
    board: str(search.board),
    sprint: str(search.sprint),
    milestone: str(search.milestone),
    area: str(search.area),
    from: str(search.from),
    to: str(search.to),
    field: str(search.field),
    interval: str(search.interval),
    by: str(search.by),
  }),
});

const dashboardsRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/dashboards',
  component: DashboardsView,
});

const dashboardRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/d/$id',
  component: DashboardView,
});

const summaryRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/p/$key/summary',
  component: ProjectSummaryView,
});

const inboxRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/p/$key/inbox',
  component: InboxView,
  validateSearch: (
    search: Record<string, unknown>,
  ): {
    tab?: string;
    classification?: string;
    origin?: string;
    sort?: string;
    view?: string;
    t?: string;
  } => ({
    tab: str(search.tab),
    classification: str(search.classification),
    origin: str(search.origin),
    sort: str(search.sort),
    view: str(search.view),
    t: str(search.t),
  }),
});

const listRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/p/$key/list',
  component: ListView,
  validateSearch: (
    search: Record<string, unknown>,
  ): { q?: string; t?: string; f?: string; g?: string } => ({
    q: str(search.q),
    t: str(search.t),
    f: str(search.f),
    g: str(search.g),
  }),
});

const milestonesRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/p/$key/milestones',
  component: MilestonesView,
});

const settingsRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/p/$key/settings',
  component: SettingsView,
  validateSearch: (search: Record<string, unknown>): { tab?: string } => ({ tab: str(search.tab) }),
});

const ticketRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/t/$key',
  component: TicketPageView,
});

const myTicketsRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/me/tickets',
  component: MyTicketsView,
  validateSearch: (search: Record<string, unknown>): { t?: string } => ({ t: str(search.t) }),
});

const profileRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/me',
  component: ProfileView,
});

const linkChatRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/integrations/link',
  validateSearch: (search: Record<string, unknown>): { token?: string } => ({
    token: typeof search.token === 'string' ? search.token : undefined,
  }),
  component: LinkChatView,
});

const adminRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/admin',
  component: AdminView,
  validateSearch: (search: Record<string, unknown>): { tab?: string } => ({ tab: str(search.tab) }),
});

const templateRoute = createRoute({
  getParentRoute: () => appLayout,
  path: '/admin/templates/$id',
  component: TemplateEditorView,
  validateSearch: (search: Record<string, unknown>): { tab?: string; type?: string } => ({
    tab: str(search.tab),
    type: str(search.type),
  }),
});

/** A public link: no account, no app shell. `$page` is `<id>-<slug>` within a space. */
const publicRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/pub/$token',
  component: FolioPublicView,
});

const publicPageRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/pub/$token/$page',
  component: FolioPublicView,
});

/** An export being printed to PDF by the worker's browser, by a short-lived token. */
const printRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/print/$token',
  component: FolioPrintView,
});

const routeTree = rootRoute.addChildren([
  publicRoute,
  publicPageRoute,
  printRoute,
  authLayout.addChildren([setupRoute, loginRoute]),
  appLayout.addChildren([
    projectsRoute,
    boardRoute,
    boardSettingsRoute,
    backlogRoute,
    timelineRoute,
    reportsRoute,
    inboxRoute,
    dashboardsRoute,
    dashboardRoute,
    summaryRoute,
    listRoute,
    milestonesRoute,
    settingsRoute,
    ticketRoute,
    myTicketsRoute,
    profileRoute,
    linkChatRoute,
    adminRoute,
    templateRoute,
  ]),
  folioRouteTree,
]);

export function createAppRouter(queryClient: QueryClient) {
  return createRouter({
    routeTree,
    context: { queryClient },
    defaultPreload: 'intent',
    defaultPreloadStaleTime: 0,
  });
}

declare module '@tanstack/react-router' {
  interface Register {
    router: ReturnType<typeof createAppRouter>;
  }
}
