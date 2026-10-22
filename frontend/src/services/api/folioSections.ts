import { api, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type SpecList = S['SpecListOut'];
export type SpecRow = S['SpecRowOut'];
export type SpecStatus = SpecRow['status'];
export type DecisionList = S['DecisionListOut'];
export type DecisionRow = S['DecisionRowOut'];
export type DecisionStatus = DecisionRow['status'];
export type DecisionStatusFilter = 'current' | 'all' | DecisionStatus;

export type SpecFilters = {
  project?: string;
  features: string[];
  status?: SpecStatus;
  owner?: string;
  q?: string;
};

export type DecisionFilters = {
  topic?: string;
  project?: string;
  status: DecisionStatusFilter;
  q?: string;
};

/** Query keys for a space's section tables (RAD-57). */
export const sectionKeys = {
  specs: (space: string, f: SpecFilters, limit: number) =>
    ['folio', 'spaces', space, 'specs', f, limit] as const,
  decisions: (space: string, f: DecisionFilters, limit: number) =>
    ['folio', 'spaces', space, 'decisions', f, limit] as const,
};

export async function fetchSpecs(space: string, f: SpecFilters, limit = 50): Promise<SpecList> {
  return unwrap(
    await api.GET('/api/v1/folio/spaces/{key}/specs', {
      params: {
        path: { key: space },
        query: {
          project: f.project,
          feature: f.project ? f.features : [],
          status: f.status,
          owner: f.owner,
          q: f.q || undefined,
          limit,
        },
      },
    }),
  );
}

export async function fetchDecisions(
  space: string,
  f: DecisionFilters,
  limit = 50,
): Promise<DecisionList> {
  return unwrap(
    await api.GET('/api/v1/folio/spaces/{key}/decisions', {
      params: {
        path: { key: space },
        query: { topic: f.topic, project: f.project, status: f.status, q: f.q || undefined, limit },
      },
    }),
  );
}
