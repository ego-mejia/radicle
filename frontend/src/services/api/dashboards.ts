import { api, unwrap } from './client';

type Visibility = 'private' | 'project' | 'instance';
type Layout = { x: number; y: number; w: number; h: number };

export const dashboardKeys = {
  list: ['dashboards'] as const,
  detail: (id: string) => ['dashboards', id] as const,
  project: (key: string) => ['dashboards', 'project', key.toUpperCase()] as const,
  // Under the tickets prefix: ticket changes refresh the widgets.
  widget: (id: string) => ['tickets', 'widget', id] as const,
};

export async function fetchDashboards() {
  return unwrap(await api.GET('/api/v1/dashboards')).items;
}

export async function fetchDashboard(id: string) {
  return unwrap(
    await api.GET('/api/v1/dashboards/{dashboard_id}', {
      params: { path: { dashboard_id: id } },
    }),
  );
}

export async function fetchProjectDashboard(key: string) {
  return unwrap(await api.GET('/api/v1/projects/{key}/dashboard', { params: { path: { key } } }));
}

export async function createDashboard(body: {
  name: string;
  visibility?: Visibility;
  project?: string | null;
}) {
  return unwrap(await api.POST('/api/v1/dashboards', { body }));
}

export async function patchDashboard(
  id: string,
  body: {
    name?: string;
    visibility?: Visibility;
    project?: string | null;
    layout?: (Layout & { id: string })[];
  },
) {
  return unwrap(
    await api.PATCH('/api/v1/dashboards/{dashboard_id}', {
      params: { path: { dashboard_id: id } },
      body,
    }),
  );
}

export async function deleteDashboard(id: string) {
  unwrap(
    await api.DELETE('/api/v1/dashboards/{dashboard_id}', {
      params: { path: { dashboard_id: id } },
    }),
  );
}

export async function addWidget(
  id: string,
  body: { widget_type: string; title: string; config: Record<string, unknown> },
) {
  return unwrap(
    await api.POST('/api/v1/dashboards/{dashboard_id}/widgets', {
      params: { path: { dashboard_id: id } },
      body,
    }),
  );
}

export async function patchWidget(
  id: string,
  widgetId: string,
  body: { title?: string; config?: Record<string, unknown> },
) {
  return unwrap(
    await api.PATCH('/api/v1/dashboards/{dashboard_id}/widgets/{widget_id}', {
      params: { path: { dashboard_id: id, widget_id: widgetId } },
      body,
    }),
  );
}

export async function deleteWidget(id: string, widgetId: string) {
  unwrap(
    await api.DELETE('/api/v1/dashboards/{dashboard_id}/widgets/{widget_id}', {
      params: { path: { dashboard_id: id, widget_id: widgetId } },
    }),
  );
}

export async function fetchWidgetData(widgetId: string) {
  return unwrap(
    await api.GET('/api/v1/widgets/{widget_id}/data', {
      params: { path: { widget_id: widgetId } },
    }),
  );
}
