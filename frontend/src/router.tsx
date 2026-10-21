import type { QueryClient } from '@tanstack/react-query';
import {
  createRootRouteWithContext,
  createRoute,
  createRouter,
  Outlet,
  redirect,
} from '@tanstack/react-router';
import { AdminView } from './features/admin/views/AdminView';
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
import { FolioAdminView } from './features/folio/views/FolioAdminView';
import { FolioApprovalsView } from './features/folio/views/FolioApprovalsView';
import { FolioTasksView } from './features/folio/views/FolioTasksView';
import { FolioTemplateView } from './features/folio/views/FolioTemplateView';
import { FolioEditView } from './features/folio/views/FolioEditView';
import { FolioHistoryView } from './features/folio/views/FolioHistoryView';
import { FolioReadView } from './features/folio/views/FolioReadView';
import { FolioSearchView } from './features/folio/views/FolioSearchView';
import { FolioCalendarView } from './features/folio/views/FolioCalendarView';
import { FolioSpaceView } from './features/folio/views/FolioSpaceView';
import { FolioHomeView } from './features/folio/views/FolioHomeView';
import { FolioPublicView } from './features/folio/views/FolioPublicView';
import { AppPage } from './pages/AppPage';
import { FolioPage } from './pages/FolioPage';
import { AuthPage } from './pages/AuthPage';
import { authKeys, fetchMe, fetchSetupStatus } from './services/api/auth';
import { fetchFolioMe, folioKeys } from './services/api/folio';
import { isApiError } from './services/api/client';

type RouterContext = { queryClient: QueryClient };

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

const str = (value: unknown) => (typeof value === 'string' && value ? value : undefined);

const rootRoute = createRootRouteWithContext<RouterContext>()({ component: Outlet });

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

/** Folio's shell: signed in like Docket, and hidden (back to Docket) without a Folio role. */
const folioLayout = createRoute({
  getParentRoute: () => rootRoute,
  id: 'folio',
  component: FolioPage,
  beforeLoad: async ({ context, location }) => {
    try {
      await context.queryClient.ensureQueryData({ queryKey: authKeys.me, queryFn: fetchMe });
    } catch (error) {
      if (!isApiError(error, 401)) throw error;
      throw redirect({ to: '/login', search: { next: location.href } });
    }
    const folio = await context.queryClient.fetchQuery({
      queryKey: folioKeys.me,
      queryFn: fetchFolioMe,
      staleTime: 60_000,
    });
    if (!folio) throw redirect({ to: '/' });
  },
});

const folioHomeRoute = createRoute({
  getParentRoute: () => folioLayout,
  path: '/folio',
  component: FolioHomeView,
});

const folioAdminRoute = createRoute({
  getParentRoute: () => folioLayout,
  path: '/folio/admin',
  component: FolioAdminView,
});

const folioTemplateRoute = createRoute({
  getParentRoute: () => folioLayout,
  path: '/folio/admin/templates/$id',
  component: FolioTemplateView,
});

const folioSpaceRoute = createRoute({
  getParentRoute: () => folioLayout,
  path: '/folio/s/$key',
  component: FolioSpaceView,
});

const folioCalendarRoute = createRoute({
  getParentRoute: () => folioLayout,
  path: '/folio/s/$key/calendar',
  component: FolioCalendarView,
});

/** `$page` is `<id>-<slug>`; only the id matters, so renamed pages keep their links. */
const folioReadRoute = createRoute({
  getParentRoute: () => folioLayout,
  path: '/folio/p/$page',
  component: FolioReadView,
});

const folioEditRoute = createRoute({
  getParentRoute: () => folioLayout,
  path: '/folio/p/$page/edit',
  component: FolioEditView,
});

const folioHistoryRoute = createRoute({
  getParentRoute: () => folioLayout,
  path: '/folio/p/$page/history',
  component: FolioHistoryView,
  validateSearch: (search: Record<string, unknown>): { from?: number; to?: number } => ({
    from: typeof search.from === 'number' ? search.from : undefined,
    to: typeof search.to === 'number' ? search.to : undefined,
  }),
});

export type FolioSearchParams = { q?: string; mode?: 'hybrid' | 'text' | 'semantic'; rql?: string };

const folioSearchRoute = createRoute({
  getParentRoute: () => folioLayout,
  path: '/folio/search',
  component: FolioSearchView,
  validateSearch: (search: Record<string, unknown>): FolioSearchParams => ({
    q: str(search.q),
    mode:
      search.mode === 'text' || search.mode === 'semantic' || search.mode === 'hybrid'
        ? search.mode
        : undefined,
    rql: str(search.rql),
  }),
});

const folioApprovalsRoute = createRoute({
  getParentRoute: () => folioLayout,
  path: '/folio/approvals',
  component: FolioApprovalsView,
});

const folioTasksRoute = createRoute({
  getParentRoute: () => folioLayout,
  path: '/folio/tasks',
  component: FolioTasksView,
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

const routeTree = rootRoute.addChildren([
  publicRoute,
  publicPageRoute,
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
    adminRoute,
    templateRoute,
  ]),
  folioLayout.addChildren([
    folioHomeRoute,
    folioAdminRoute,
    folioTemplateRoute,
    folioSpaceRoute,
    folioCalendarRoute,
    folioReadRoute,
    folioEditRoute,
    folioHistoryRoute,
    folioSearchRoute,
    folioApprovalsRoute,
    folioTasksRoute,
  ]),
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
