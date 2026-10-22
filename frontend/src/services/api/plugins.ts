// Plugins (ADR 0043): instance admins install JSON manifests; Folio reads the editor
// blocks of the ones that are on.

import { api, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type Plugin = S['PluginOut'];
export type PluginList = S['PluginsOut'];
export type PluginBlock = S['PluginBlockOut'];
export type PluginBlockField = S['PluginBlockField'];

export const pluginKeys = {
  admin: ['admin', 'plugins'] as const,
  blocks: ['folio', 'plugin-blocks'] as const,
};

export async function fetchPlugins(): Promise<PluginList> {
  return unwrap(await api.GET('/api/v1/admin/plugins'));
}

export async function installPlugin(manifest: Record<string, unknown>): Promise<Plugin> {
  return unwrap(await api.POST('/api/v1/admin/plugins', { body: { manifest } }));
}

export async function installExample(key: string): Promise<Plugin> {
  return unwrap(
    await api.POST('/api/v1/admin/plugins/examples/{key}', { params: { path: { key } } }),
  );
}

export async function setPluginEnabled(key: string, enabled: boolean): Promise<Plugin> {
  return unwrap(
    await api.PATCH('/api/v1/admin/plugins/{key}', {
      params: { path: { key } },
      body: { enabled },
    }),
  );
}

export async function deletePlugin(key: string): Promise<void> {
  unwrap(await api.DELETE('/api/v1/admin/plugins/{key}', { params: { path: { key } } }));
}

export async function fetchPluginBlocks(): Promise<PluginBlock[]> {
  return unwrap(await api.GET('/api/v1/folio/plugin-blocks')).items;
}
