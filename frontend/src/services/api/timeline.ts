import { api, unwrap } from './client';

export type TimelineParams = { group_by?: 'milestone' | 'area'; q?: string };

export const timelineKeys = {
  // Under the tickets prefix so date changes anywhere refresh it.
  data: (project: string, params: TimelineParams) =>
    ['tickets', 'timeline', project.toUpperCase(), params] as const,
};

export async function fetchTimeline(project: string, params: TimelineParams) {
  return unwrap(
    await api.GET('/api/v1/projects/{key}/timeline', {
      params: {
        path: { key: project },
        query: { group_by: params.group_by, q: params.q || undefined },
      },
    }),
  );
}
