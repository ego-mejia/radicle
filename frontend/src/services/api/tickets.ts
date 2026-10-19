import { api, unwrap } from './client';
import type { Resolution, TicketCreate, TicketPatch, TicketType } from './types';

export const ticketKeys = {
  all: ['tickets'] as const,
  search: (q: string) => ['tickets', 'search', q] as const,
  detail: (key: string) => ['tickets', 'detail', key.toUpperCase()] as const,
  transitions: (key: string) => ['tickets', 'transitions', key.toUpperCase()] as const,
  children: (key: string) => ['tickets', 'children', key.toUpperCase()] as const,
  comments: (key: string) => ['tickets', 'comments', key.toUpperCase()] as const,
  history: (key: string) => ['tickets', 'history', key.toUpperCase()] as const,
};

const path = (key: string) => ({ params: { path: { key } } });

export async function searchTickets(q: string, cursor?: string, limit = 50) {
  return unwrap(await api.GET('/api/v1/tickets', { params: { query: { q, cursor, limit } } }));
}

/** Every page of a query; used by the board, which shows whole columns. */
export async function searchAll(q: string, max = 1000) {
  const first = await searchTickets(q, undefined, 200);
  const items = [...first.items];
  let cursor = first.next_cursor ?? undefined;
  while (cursor && items.length < max) {
    const page = await searchTickets(q, cursor, 200);
    items.push(...page.items);
    cursor = page.next_cursor ?? undefined;
  }
  return { ...first, items };
}

export async function fetchTicket(key: string) {
  return unwrap(await api.GET('/api/v1/tickets/{key}', path(key)));
}

export async function createTicket(project: string, body: TicketCreate) {
  return unwrap(await api.POST('/api/v1/projects/{key}/tickets', { ...path(project), body }));
}

export async function patchTicket(
  key: string,
  version: number,
  body: Omit<TicketPatch, 'expected_version'>,
) {
  return unwrap(
    await api.PATCH('/api/v1/tickets/{key}', {
      ...path(key),
      body: { ...body, expected_version: version },
    }),
  );
}

export async function deleteTicket(key: string) {
  unwrap(await api.DELETE('/api/v1/tickets/{key}', path(key)));
}

export async function fetchTransitions(key: string, includeUnavailable = true) {
  return unwrap(
    await api.GET('/api/v1/tickets/{key}/transitions', {
      params: { path: { key }, query: { include_unavailable: includeUnavailable } },
    }),
  );
}

export type Move = {
  to: string;
  resolution?: Resolution | null;
  transition?: string;
  comment?: string | null;
  force?: boolean;
};

export async function transitionTicket(key: string, move: Move) {
  return unwrap(
    await api.POST('/api/v1/tickets/{key}/transitions', {
      ...path(key),
      body: {
        to_status: move.to,
        resolution: move.resolution ?? null,
        transition: move.transition ?? null,
        comment: move.comment || null,
        force: move.force ?? false,
      },
    }),
  );
}

export async function changeType(key: string, type: TicketType, area?: string | null) {
  return unwrap(
    await api.POST('/api/v1/tickets/{key}/type', {
      ...path(key),
      body: { type, area: area ?? null },
    }),
  );
}

export async function setChecklistItem(key: string, index: number, checked: boolean) {
  return unwrap(
    await api.PATCH('/api/v1/tickets/{key}/checklist/{index}', {
      params: { path: { key, index } },
      body: { checked },
    }),
  );
}

export async function fetchChildren(key: string) {
  return unwrap(await api.GET('/api/v1/tickets/{key}/children', path(key))).items;
}

export async function addCollaborator(key: string, handle: string) {
  return unwrap(
    await api.PUT('/api/v1/tickets/{key}/collaborators/{handle}', {
      params: { path: { key, handle } },
    }),
  );
}

export async function removeCollaborator(key: string, handle: string) {
  return unwrap(
    await api.DELETE('/api/v1/tickets/{key}/collaborators/{handle}', {
      params: { path: { key, handle } },
    }),
  );
}

export async function addLink(key: string, type: string, target: string) {
  return unwrap(
    await api.POST('/api/v1/tickets/{key}/links', { ...path(key), body: { type, target } }),
  );
}

export async function removeLink(id: string) {
  unwrap(await api.DELETE('/api/v1/links/{link_id}', { params: { path: { link_id: id } } }));
}

export async function fetchHistory(key: string, cursor?: string) {
  return unwrap(
    await api.GET('/api/v1/tickets/{key}/history', {
      params: { path: { key }, query: { limit: 100, cursor } },
    }),
  );
}
