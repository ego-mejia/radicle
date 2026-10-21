import { api, unwrap } from './client';
import type { components } from './schema';

export type AiSettings = components['schemas']['AiSettingsOut'];
export type AiSettingsPatch = components['schemas']['AiSettingsIn'];
export type AiProvider = AiSettings['provider'];

export const aiKeys = { settings: ['admin', 'ai'] as const };

export async function fetchAiSettings() {
  return unwrap(await api.GET('/api/v1/admin/ai'));
}

export async function saveAiSettings(body: AiSettingsPatch) {
  return unwrap(await api.PUT('/api/v1/admin/ai', { body }));
}

export async function testAi() {
  return unwrap(await api.POST('/api/v1/admin/ai/test'));
}
