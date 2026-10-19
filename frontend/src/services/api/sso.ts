import { api, unwrap } from './client';

export const ssoKeys = {
  providers: ['sso-providers'] as const,
  settings: ['instance-settings'] as const,
};

export type ProviderInput = {
  name?: string;
  issuer_url?: string;
  client_id?: string;
  client_secret?: string;
  allowed_domains?: string[];
  auto_create_users?: boolean;
  group_claim?: string | null;
  group_mapping?: Record<string, string>;
  enabled?: boolean;
};

export async function fetchProviders() {
  return unwrap(await api.GET('/api/v1/admin/sso-providers')).items;
}

export async function createProvider(body: ProviderInput) {
  return unwrap(await api.POST('/api/v1/admin/sso-providers', { body }));
}

export async function patchProvider(id: string, body: ProviderInput) {
  return unwrap(
    await api.PATCH('/api/v1/admin/sso-providers/{provider_id}', {
      params: { path: { provider_id: id } },
      body,
    }),
  );
}

export async function deleteProvider(id: string) {
  unwrap(
    await api.DELETE('/api/v1/admin/sso-providers/{provider_id}', {
      params: { path: { provider_id: id } },
    }),
  );
}

export async function testProvider(id: string) {
  return unwrap(
    await api.POST('/api/v1/admin/sso-providers/{provider_id}/test', {
      params: { path: { provider_id: id } },
    }),
  );
}

export async function fetchInstanceSettings() {
  return unwrap(await api.GET('/api/v1/admin/settings'));
}

export async function patchInstanceSettings(body: { password_login_enabled?: boolean }) {
  return unwrap(await api.PATCH('/api/v1/admin/settings', { body }));
}
