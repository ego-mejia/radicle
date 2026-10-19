import { api, unwrap } from './client';

export const authKeys = { me: ['me'] as const, setup: ['setup-status'] as const };

export async function fetchMe() {
  return unwrap(await api.GET('/api/v1/me'));
}

export async function fetchSetupStatus() {
  return unwrap(await api.GET('/api/v1/setup/status'));
}

export async function setup(body: {
  handle: string;
  display_name: string;
  email: string;
  password: string;
}) {
  return unwrap(await api.POST('/api/v1/setup', { body }));
}

export async function login(email: string, password: string) {
  return unwrap(await api.POST('/api/v1/auth/login', { body: { email, password } }));
}

export async function logout() {
  const result = await api.POST('/api/v1/auth/logout');
  if (!result.response.ok && result.response.status !== 401) unwrap(result);
}

export async function updateMe(body: {
  display_name?: string;
  current_password?: string;
  new_password?: string;
}) {
  return unwrap(await api.PATCH('/api/v1/me', { body }));
}

export async function fetchMyTokens() {
  return unwrap(await api.GET('/api/v1/me/tokens')).items;
}

export async function createMyToken(name: string) {
  return unwrap(await api.POST('/api/v1/me/tokens', { body: { name } }));
}

export async function revokeMyToken(id: string) {
  unwrap(await api.DELETE('/api/v1/me/tokens/{token_id}', { params: { path: { token_id: id } } }));
}

export async function fetchAuthOptions() {
  return unwrap(await api.GET('/api/v1/auth/options'));
}
