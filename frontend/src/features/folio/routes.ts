import { createRoute, redirect } from '@tanstack/react-router';
import { rootRoute, str } from '../../routerRoot';
import { authKeys, fetchMe } from '../../services/api/auth';
import { isApiError } from '../../services/api/client';
import { fetchFolioMe, folioKeys } from '../../services/api/folio';
import { FolioAdminView } from './views/FolioAdminView';
import { FolioApprovalsView } from './views/FolioApprovalsView';
import { FolioCalendarView } from './views/FolioCalendarView';
import { FolioEditView } from './views/FolioEditView';
import { FolioHistoryView } from './views/FolioHistoryView';
import { FolioHomeView } from './views/FolioHomeView';
import { FolioPage } from '../../pages/FolioPage';
import { FolioReadView } from './views/FolioReadView';
import { FolioSearchView } from './views/FolioSearchView';
import { FolioSpaceView } from './views/FolioSpaceView';
import { FolioTasksView } from './views/FolioTasksView';
import { FolioTemplateView } from './views/FolioTemplateView';

// Folio's routes, apart from router.tsx so each stays under 500 lines.

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

export const folioRouteTree = folioLayout.addChildren([
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
]);
