import { api, unwrap } from './client';
import type { components } from './schema';

export type AssistantSettings = components['schemas']['AssistantSettingsOut'];
export type AssistantSettingsPatch = components['schemas']['AssistantSettingsIn'];

export const assistantKeys = { settings: ['admin', 'assistant'] as const };

export async function fetchAssistantSettings() {
  return unwrap(await api.GET('/api/v1/admin/assistant'));
}

export async function saveAssistantSettings(body: AssistantSettingsPatch) {
  return unwrap(await api.PUT('/api/v1/admin/assistant', { body }));
}

export async function testAssistant() {
  return unwrap(await api.POST('/api/v1/admin/assistant/test'));
}
