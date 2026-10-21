// Docket tickets inside Folio docs (4.1 to 4.4): live previews for smart links, the ticket
// table by RQL, a doc's links, a ticket's or milestone's docs, creating a ticket from a
// selection, and a build spec's deliverables as tickets.

import { api, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type FolioTicket = S['FolioTicketOut'];
export type FolioTicketPreview = S['FolioTicketPreview'];
export type FolioTicketLink = S['FolioTicketLinkOut'];
export type FolioTicketQuery = S['FolioTicketQueryOut'];
export type TicketDoc = S['TicketDocOut'];
export type TicketFromTextIn = S['TicketFromTextIn'];
export type BuildSpecItem = S['BuildSpecItemOut'];
export type BuildSpecTicketsIn = S['BuildSpecTicketsIn'];

export const ticketKeys = {
  preview: (key: string) => ['folio', 'tickets', 'preview', key] as const,
  query: (rql: string, limit: number) => ['folio', 'tickets', 'query', rql, limit] as const,
  links: (nodeId: string) => ['folio', 'nodes', nodeId, 'ticket-links'] as const,
  docs: (key: string) => ['folio', 'tickets', key, 'docs'] as const,
  buildSpec: (nodeId: string) => ['folio', 'nodes', nodeId, 'build-spec'] as const,
  milestoneDocs: (ref: string) => ['folio', 'milestones', ref, 'docs'] as const,
};

/** A smart link's key, as typed or pasted: `PA-4`, or a Docket link `…/t/PA-4`. */
const KEY = /^([A-Za-z][A-Za-z0-9]{1,9}-\d{1,9})$/;
const DOCKET_URL = /^https?:\/\/\S+\/t\/([A-Za-z][A-Za-z0-9]{1,9}-\d{1,9})\/?$/;

export function ticketKeyIn(text: string): string | null {
  const trimmed = text.trim();
  const match = KEY.exec(trimmed) ?? DOCKET_URL.exec(trimmed);
  return match?.[1] ? match[1].toUpperCase() : null;
}

// Smart links on one page ask together: keys asked in the same tick share one request.
let pending: Map<string, ((p: FolioTicketPreview) => void)[]> | null = null;

async function flush(batch: Map<string, ((p: FolioTicketPreview) => void)[]>) {
  const keys = [...batch.keys()];
  try {
    const found = unwrap(
      await api.GET('/api/v1/folio/tickets/preview', {
        params: { query: { keys: keys.join(',') } },
      }),
    ).items;
    const byKey = new Map(found.map((p) => [p.key, p]));
    for (const [key, waiting] of batch) {
      const preview = byKey.get(key) ?? { key, restricted: true, ticket: null };
      for (const resolve of waiting) resolve(preview);
    }
  } catch {
    for (const [key, waiting] of batch) {
      for (const resolve of waiting) resolve({ key, restricted: true, ticket: null });
    }
  }
}

export function fetchTicketPreview(key: string): Promise<FolioTicketPreview> {
  return new Promise((resolve) => {
    if (!pending) {
      const batch = new Map<string, ((p: FolioTicketPreview) => void)[]>();
      pending = batch;
      setTimeout(() => {
        pending = null;
        void flush(batch);
      }, 0);
    }
    const waiting = pending.get(key) ?? [];
    waiting.push(resolve);
    pending.set(key, waiting);
  });
}

export async function queryTickets(rql: string, limit: number): Promise<FolioTicketQuery> {
  return unwrap(
    await api.GET('/api/v1/folio/tickets/query', { params: { query: { rql, limit } } }),
  );
}

export async function fetchTicketLinks(nodeId: string): Promise<FolioTicketLink[]> {
  const path = { node_id: nodeId };
  return unwrap(await api.GET('/api/v1/folio/nodes/{node_id}/ticket-links', { params: { path } }))
    .items;
}

export async function fetchTicketDocs(key: string): Promise<TicketDoc[]> {
  return unwrap(await api.GET('/api/v1/folio/links', { params: { query: { ticket: key } } })).items;
}

export async function createTicketFromText(
  nodeId: string,
  body: TicketFromTextIn,
): Promise<FolioTicketLink> {
  const path = { node_id: nodeId };
  return unwrap(
    await api.POST('/api/v1/folio/nodes/{node_id}/tickets', { params: { path }, body }),
  );
}

export async function fetchMilestoneDocs(project: string, name: string): Promise<TicketDoc[]> {
  const milestone = `${project}:${name}`;
  return unwrap(await api.GET('/api/v1/folio/links', { params: { query: { milestone } } })).items;
}

export async function fetchBuildSpecItems(nodeId: string): Promise<BuildSpecItem[]> {
  const path = { node_id: nodeId };
  return unwrap(
    await api.GET('/api/v1/folio/nodes/{node_id}/build-spec/items', { params: { path } }),
  ).items;
}

export async function createBuildSpecTickets(
  nodeId: string,
  body: BuildSpecTicketsIn,
): Promise<BuildSpecItem[]> {
  const path = { node_id: nodeId };
  return unwrap(
    await api.POST('/api/v1/folio/nodes/{node_id}/build-spec/tickets', { params: { path }, body }),
  ).items;
}
