import { api, unwrap } from './client';

export const systemKeys = {
  health: ['system', 'health'] as const,
  setupStatus: ['system', 'setup-status'] as const,
};

export async function fetchHealth() {
  return unwrap(await api.GET('/api/v1/health'));
}

export async function fetchSetupStatus() {
  return unwrap(await api.GET('/api/v1/setup/status'));
}
