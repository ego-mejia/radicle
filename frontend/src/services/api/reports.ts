import { api, unwrap } from './client';
import type { ReportType } from './types';

export type ReportParams = {
  project?: string;
  board?: string;
  sprint?: string;
  milestone?: string;
  q?: string;
  from?: string;
  to?: string;
  field?: string;
  interval?: 'day' | 'week';
  by?: 'ticket' | 'milestone' | 'area' | 'assignee';
};

export const reportKeys = {
  // Under the tickets prefix: any ticket change refreshes the reports.
  data: (type: ReportType, params: ReportParams) => ['tickets', 'report', type, params] as const,
};

function clean(params: ReportParams): Record<string, string> {
  return Object.fromEntries(
    Object.entries(params).filter((e): e is [string, string] => Boolean(e[1])),
  );
}

export async function fetchReport(type: ReportType, params: ReportParams) {
  return unwrap(
    await api.GET('/api/v1/reports/{kind}', {
      params: { path: { kind: type }, query: clean(params) },
    }),
  );
}

/** Same data as CSV; a plain link downloads it with the session cookie. */
export function reportCsvUrl(type: ReportType, params: ReportParams): string {
  return `/api/v1/reports/${type}.csv?${new URLSearchParams(clean(params)).toString()}`;
}
