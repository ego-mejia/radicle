import { api, unwrap } from './client';
import type { BlockedPolicy, TemplateConfig, WorkflowConf } from './types';

export type Mappings = Record<string, string | Record<string, string>>;

export const templateKeys = {
  all: ['templates'] as const,
  list: (archived: boolean) => ['templates', 'list', archived] as const,
  detail: (id: string) => ['templates', 'detail', id] as const,
  runs: (id: string) => ['templates', 'runs', id] as const,
};

const id = (templateId: string) => ({ params: { path: { template_id: templateId } } });
const key = (projectKey: string) => ({ params: { path: { key: projectKey } } });

export async function fetchTemplates(includeArchived = false) {
  return unwrap(
    await api.GET('/api/v1/templates', {
      params: { query: { include_archived: includeArchived } },
    }),
  ).items;
}

export async function fetchTemplate(templateId: string) {
  return unwrap(await api.GET('/api/v1/templates/{template_id}', id(templateId)));
}

export async function createTemplate(body: { name: string; description_md?: string }) {
  return unwrap(await api.POST('/api/v1/templates', { body }));
}

export async function patchTemplate(
  templateId: string,
  body: {
    name?: string;
    description_md?: string;
    config?: TemplateConfig;
    status_mappings?: Mappings | null;
  },
) {
  return unwrap(await api.PATCH('/api/v1/templates/{template_id}', { ...id(templateId), body }));
}

export async function setTemplateArchived(templateId: string, archived: boolean) {
  const url = archived
    ? '/api/v1/templates/{template_id}/archive'
    : '/api/v1/templates/{template_id}/unarchive';
  return unwrap(await api.POST(url, id(templateId)));
}

export async function fetchSyncRuns(templateId: string) {
  return unwrap(await api.GET('/api/v1/templates/{template_id}/sync-runs', id(templateId))).items;
}

export async function retrySyncRun(templateId: string, runId: string) {
  return unwrap(
    await api.POST('/api/v1/templates/{template_id}/sync-runs/{run_id}/retry', {
      params: { path: { template_id: templateId, run_id: runId } },
    }),
  );
}

export async function saveAsTemplate(projectKey: string, body: { name: string }) {
  return unwrap(
    await api.POST('/api/v1/projects/{key}/save-as-template', { ...key(projectKey), body }),
  );
}

export async function detachProject(projectKey: string) {
  return unwrap(await api.POST('/api/v1/projects/{key}/detach', key(projectKey)));
}

export async function putWorkflow(
  projectKey: string,
  ticketType: 'task' | 'bug' | 'draft',
  workflow: WorkflowConf,
  statusMappings?: Mappings | null,
) {
  return unwrap(
    await api.PUT('/api/v1/projects/{key}/workflows/{ticket_type}', {
      params: { path: { key: projectKey, ticket_type: ticketType } },
      body: { workflow, status_mappings: statusMappings ?? null },
    }),
  );
}

export async function putProjectSettings(projectKey: string, blockedPolicy: BlockedPolicy) {
  return unwrap(
    await api.PUT('/api/v1/projects/{key}/settings', {
      ...key(projectKey),
      body: { blocked_policy: blockedPolicy },
    }),
  );
}
