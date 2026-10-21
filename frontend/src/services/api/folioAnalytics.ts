import { api, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type PageAnalytics = S['PageAnalyticsOut'];
export type SiteAnalytics = S['SiteAnalyticsOut'];
export type AnalyticsDay = S['DayOut'];

/** Query keys for Folio analytics (Folio 5.9). */
export const analyticsKeys = {
  page: (id: string, days: number) => ['folio', 'analytics', 'page', id, days] as const,
  site: (days: number) => ['folio', 'analytics', 'site', days] as const,
};

/** Counts one read of the page; the reader never waits on it. */
export async function recordView(nodeId: string): Promise<void> {
  unwrap(await api.POST('/api/v1/folio/analytics/views', { body: { node_id: nodeId } }));
}

/** The result someone opened from a search. */
export async function recordSearchClick(searchId: string, nodeId: string): Promise<void> {
  unwrap(
    await api.POST('/api/v1/folio/analytics/searches/{search_id}/click', {
      params: { path: { search_id: searchId } },
      body: { node_id: nodeId },
    }),
  );
}

export async function fetchPageAnalytics(nodeId: string, days = 30): Promise<PageAnalytics> {
  return unwrap(
    await api.GET('/api/v1/folio/analytics/pages/{node_id}', {
      params: { path: { node_id: nodeId }, query: { days } },
    }),
  );
}

export async function fetchSiteAnalytics(days = 30): Promise<SiteAnalytics> {
  return unwrap(await api.GET('/api/v1/folio/analytics/site', { params: { query: { days } } }));
}
