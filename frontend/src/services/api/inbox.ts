import { api, unwrap } from './client';
import type { Classification, InboxTab, Priority } from './types';

export type InboxParams = {
  tab?: InboxTab;
  classification?: Classification;
  origin?: 'team' | 'user';
  sort?: 'votes' | 'age' | 'score';
};

export const inboxKeys = {
  // Under the tickets prefix: triage changes tickets.
  list: (project: string, params: InboxParams) =>
    ['tickets', 'inbox', project.toUpperCase(), params] as const,
};

export async function fetchInbox(project: string, params: InboxParams) {
  return unwrap(
    await api.GET('/api/v1/projects/{key}/inbox', {
      params: { path: { key: project }, query: params },
    }),
  );
}

export async function approveItem(
  key: string,
  body: {
    type: 'task' | 'bug';
    area: string;
    milestone?: string | null;
    priority?: Priority | null;
    assignee?: string | null;
  },
) {
  return unwrap(
    await api.POST('/api/v1/tickets/{key}/inbox/approve', { params: { path: { key } }, body }),
  );
}

export async function discardItem(key: string, publicComment: string | null) {
  return unwrap(
    await api.POST('/api/v1/tickets/{key}/inbox/discard', {
      params: { path: { key } },
      body: { public_comment: publicComment },
    }),
  );
}

export async function duplicateItem(key: string, original: string) {
  return unwrap(
    await api.POST('/api/v1/tickets/{key}/inbox/duplicate', {
      params: { path: { key } },
      body: { original },
    }),
  );
}

/** Score or reclassify an item; the patch needs the current version, so it reads it first. */
export async function scoreItem(
  key: string,
  body: { impact?: number | null; effort?: number | null; classification?: Classification },
) {
  const current = unwrap(await api.GET('/api/v1/tickets/{key}', { params: { path: { key } } }));
  return unwrap(
    await api.PATCH('/api/v1/tickets/{key}', {
      params: { path: { key } },
      body: { ...body, expected_version: current.version },
    }),
  );
}

export type InboxSettingsPatch = {
  enabled?: boolean;
  public_slug?: string;
  title?: string;
  intro_md?: string;
  thank_you_md?: string;
  allowed_classifications?: string[];
  require_email?: boolean;
  allow_attachments?: boolean;
  max_attachments?: number;
  captcha?: string;
  captcha_site_key?: string;
  captcha_secret?: string;
  auto_tags?: string[];
};

export async function fetchInboxSettings(key: string) {
  return unwrap(
    await api.GET('/api/v1/projects/{key}/inbox-settings', { params: { path: { key } } }),
  );
}

export async function putInboxSettings(key: string, body: InboxSettingsPatch) {
  return unwrap(
    await api.PUT('/api/v1/projects/{key}/inbox-settings', { params: { path: { key } }, body }),
  );
}
