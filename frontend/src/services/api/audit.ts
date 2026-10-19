import { api, unwrap } from './client';

export type AuditFilters = {
  actor?: string;
  action?: string;
  project?: string;
  from?: string;
  to?: string;
};

export const auditKeys = {
  list: (filters: AuditFilters) => ['audit', filters] as const,
};

function clean(filters: AuditFilters): Record<string, string> {
  return Object.fromEntries(
    Object.entries(filters).filter((e): e is [string, string] => Boolean(e[1])),
  );
}

export async function fetchAudit(filters: AuditFilters, cursor?: string) {
  return unwrap(
    await api.GET('/api/v1/audit', {
      params: { query: { ...clean(filters), cursor } },
    }),
  );
}

export function auditCsvUrl(filters: AuditFilters): string {
  return `/api/v1/audit.csv?${new URLSearchParams(clean(filters)).toString()}`;
}

export const AUDIT_GROUPS = [
  'user',
  'token',
  'agent',
  'project',
  'member',
  'group_role',
  'group',
  'permission',
  'security_level',
  'ticket',
  'template',
  'workflow',
  'inbox',
  'sso',
  'settings',
] as const;
