import { api, unwrap } from './client';
import type { User } from './types';

export const adminKeys = {
  users: ['admin', 'users'] as const,
  tokens: (handle: string) => ['admin', 'tokens', handle] as const,
};

export async function fetchUsers(): Promise<User[]> {
  const users: User[] = [];
  let cursor: string | undefined;
  do {
    const page = unwrap(
      await api.GET('/api/v1/users', { params: { query: { limit: 200, cursor } } }),
    );
    users.push(...page.items);
    cursor = page.next_cursor ?? undefined;
  } while (cursor);
  return users;
}

export async function createUser(body: {
  handle: string;
  display_name: string;
  email: string;
  password: string;
  is_instance_admin?: boolean;
}) {
  return unwrap(await api.POST('/api/v1/users', { body }));
}

export async function createAgent(body: { handle: string; display_name: string }) {
  return unwrap(await api.POST('/api/v1/agents', { body }));
}

export async function patchUser(
  handle: string,
  body: {
    display_name?: string;
    is_active?: boolean;
    is_instance_admin?: boolean;
    password?: string;
  },
) {
  return unwrap(await api.PATCH('/api/v1/users/{handle}', { params: { path: { handle } }, body }));
}

export async function fetchUserTokens(handle: string) {
  return unwrap(await api.GET('/api/v1/users/{handle}/tokens', { params: { path: { handle } } }))
    .items;
}

export async function createAgentToken(handle: string, name: string) {
  return unwrap(
    await api.POST('/api/v1/users/{handle}/tokens', {
      params: { path: { handle } },
      body: { name },
    }),
  );
}

export async function revokeUserToken(handle: string, id: string) {
  unwrap(
    await api.DELETE('/api/v1/users/{handle}/tokens/{token_id}', {
      params: { path: { handle, token_id: id } },
    }),
  );
}
