import { api, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type Notification = S['NotificationOut'];
export type NotificationsPage = S['NotificationsPage'];
export type NotificationPreferences = S['NotificationPreferencesOut'];
export type NotificationPreference = S['PreferenceOut'];
export type NotificationChannel = 'in_app' | 'email';

export const notificationKeys = {
  all: ['notifications'] as const,
  list: ['notifications', 'list'] as const,
  preferences: ['notifications', 'preferences'] as const,
};

export const STREAM_URL = '/api/v1/me/notifications/stream';

export async function fetchNotifications(limit = 20): Promise<NotificationsPage> {
  return unwrap(await api.GET('/api/v1/me/notifications', { params: { query: { limit } } }));
}

/** Marks these notifications read, or all of them without ids. */
export async function markRead(ids?: string[]): Promise<{ marked: number; unread: number }> {
  return unwrap(await api.POST('/api/v1/me/notifications/read', { body: ids ? { ids } : {} }));
}

export async function fetchNotificationPreferences(): Promise<NotificationPreferences> {
  return unwrap(await api.GET('/api/v1/me/notification-preferences'));
}

export async function setNotificationPreference(body: {
  app: string;
  type: string;
  channel: NotificationChannel;
  enabled: boolean;
}): Promise<NotificationPreferences> {
  return unwrap(await api.PUT('/api/v1/me/notification-preferences', { body }));
}
