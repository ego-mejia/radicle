import { api, isApiError, unwrap } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type FolioMe = S['FolioMeOut'];
export type FolioGrant = S['GrantOut'];
export type FolioGrantIn = S['GrantIn'];
export type FolioSpace = S['SpaceOut'];
export type FolioSpaceIn = S['SpaceIn'];
export type FolioTreeItem = S['TreeItem'];
export type FolioNodeRef = S['NodeRef'];
export type FolioNode = S['NodeOut'];
export type FolioNodeIn = S['NodeIn'];
export type FolioMoveIn = S['NodeMoveIn'];
export type FolioTemplate = S['FolioTemplateOut'];
export type FolioLinkPreview = S['LinkPreviewOut'];
export type FolioTemplateIn = S['FolioTemplateIn'];
export type FolioTemplatePatch = S['FolioTemplatePatch'];
export type NodeFromTemplateIn = S['NodeFromTemplateIn'];
export type FolioDraft = S['DraftOut'];
export type FolioDraftIn = S['DraftIn'];
export type FolioPublishIn = S['PublishIn'];
export type FolioVersion = S['VersionOut'];
export type FolioVersionContent = S['VersionContentOut'];
export type FolioSnapshot = S['SnapshotOut'];
export type FolioSnapshotContent = S['SnapshotContentOut'];
export type FolioDiff = S['DiffOut'];
export type FolioSubmission = S['SubmissionOut'];
export type FolioSubmissionDetail = S['SubmissionDetailOut'];
export type FolioSchema = S['MetadataSchemaOut'];
export type FolioEntry = S['EntryOut'];
export type FolioEntryIn = S['EntryIn'];
export type FolioEntryPatch = S['EntryPatch'];
export type FolioCatalog = 'doc-types' | 'audiences' | 'languages';
export type FolioHit = S['HitOut'];
export type FolioSearch = S['SearchOut'];
export type FolioDoc = S['DocOut'];
export type FolioAsset = S['AssetOut'];
export type SearchMode = 'hybrid' | 'text' | 'semantic';
export type SubmissionStatus = 'pending' | 'approved' | 'rejected' | 'superseded';

export const folioKeys = {
  me: ['folio', 'me'] as const,
  grants: ['folio', 'grants'] as const,
  spaces: ['folio', 'spaces'] as const,
  space: (key: string) => ['folio', 'spaces', key] as const,
  tree: (key: string) => ['folio', 'spaces', key, 'tree'] as const,
  posts: (key: string) => ['folio', 'spaces', key, 'posts'] as const,
  node: (id: string) => ['folio', 'nodes', id] as const,
  draft: (id: string) => ['folio', 'nodes', id, 'draft'] as const,
  versions: (id: string) => ['folio', 'nodes', id, 'versions'] as const,
  version: (id: string, n: number) => ['folio', 'nodes', id, 'versions', n] as const,
  diff: (id: string, from: number, to: number) => ['folio', 'nodes', id, 'diff', from, to] as const,
  snapshots: (id: string) => ['folio', 'nodes', id, 'snapshots'] as const,
  snapshot: (id: string, sid: string) => ['folio', 'nodes', id, 'snapshots', sid] as const,
  schema: ['folio', 'metadata-schema'] as const,
  template: (id: string) => ['folio', 'template', id] as const,
  linkPreview: (url: string) => ['folio', 'link-preview', url] as const,
  templates: (kind: 'page' | 'space', space?: string) =>
    ['folio', 'templates', kind, space ?? 'all'] as const,
  catalog: (name: FolioCatalog) => ['folio', 'catalog', name] as const,
  submissions: (status?: SubmissionStatus) => ['folio', 'submissions', status ?? 'all'] as const,
  submission: (id: string) => ['folio', 'submission', id] as const,
  search: (q: string, mode: SearchMode, filters: SearchFilters) =>
    ['folio', 'search', q, mode, filters] as const,
  query: (rql: string) => ['folio', 'query', rql] as const,
};

/** The node id inside a page URL segment like `9f3c…-my-page`. */
export function nodeIdFrom(segment: string): string {
  return segment.slice(0, 36);
}

/** Path to read a node: `/folio/p/<id>-<slug>`. */
export function nodePath(node: { id: string; slug: string }): string {
  return `/folio/p/${node.id}-${node.slug}`;
}

/** Your Folio role, or null when no grant reaches you (Folio is hidden then). */
export async function fetchFolioMe(): Promise<FolioMe | null> {
  try {
    return unwrap(await api.GET('/api/v1/folio/me'));
  } catch (error) {
    if (isApiError(error, 404)) return null;
    throw error;
  }
}

export async function fetchFolioGrants(): Promise<FolioGrant[]> {
  return unwrap(await api.GET('/api/v1/folio/admin/grants')).items;
}

export async function setFolioGrant(body: FolioGrantIn): Promise<FolioGrant> {
  return unwrap(await api.POST('/api/v1/folio/admin/grants', { body }));
}

export async function removeFolioGrant(id: string): Promise<void> {
  unwrap(
    await api.DELETE('/api/v1/folio/admin/grants/{grant_id}', {
      params: { path: { grant_id: id } },
    }),
  );
}

// --- spaces and the tree -------------------------------------------------------------

export async function fetchSpaces(): Promise<FolioSpace[]> {
  return unwrap(await api.GET('/api/v1/folio/spaces')).items;
}

export async function fetchSpace(key: string): Promise<FolioSpace> {
  return unwrap(await api.GET('/api/v1/folio/spaces/{key}', { params: { path: { key } } }));
}

export async function createSpace(body: FolioSpaceIn): Promise<FolioSpace> {
  return unwrap(await api.POST('/api/v1/folio/spaces', { body }));
}

export async function fetchPersonalSpace(): Promise<FolioSpace> {
  return unwrap(await api.GET('/api/v1/folio/me/personal-space'));
}

export async function fetchTree(key: string): Promise<FolioTreeItem[]> {
  return unwrap(await api.GET('/api/v1/folio/spaces/{key}/tree', { params: { path: { key } } }));
}

export async function fetchPosts(key: string): Promise<FolioNodeRef[]> {
  return unwrap(await api.GET('/api/v1/folio/spaces/{key}/posts', { params: { path: { key } } }))
    .items;
}

// --- nodes, drafts and publishing ----------------------------------------------------

export async function fetchNode(id: string): Promise<FolioNode> {
  return unwrap(
    await api.GET('/api/v1/folio/nodes/{node_id}', { params: { path: { node_id: id } } }),
  );
}

export async function createNode(body: FolioNodeIn): Promise<FolioNode> {
  return unwrap(await api.POST('/api/v1/folio/nodes', { body }));
}

export type FolioNodePatch = S['NodePatch'];

/** Title, icon and cover; `null` clears the icon or the cover. */
export async function patchNode(id: string, body: FolioNodePatch): Promise<FolioNode> {
  return unwrap(
    await api.PATCH('/api/v1/folio/nodes/{node_id}', { params: { path: { node_id: id } }, body }),
  );
}

export async function moveNode(id: string, body: FolioMoveIn): Promise<FolioNode> {
  return unwrap(
    await api.POST('/api/v1/folio/nodes/{node_id}/move', {
      params: { path: { node_id: id } },
      body,
    }),
  );
}

export async function fetchDraft(id: string): Promise<FolioDraft> {
  return unwrap(
    await api.GET('/api/v1/folio/nodes/{node_id}/draft', { params: { path: { node_id: id } } }),
  );
}

export async function saveDraft(id: string, body: FolioDraftIn): Promise<FolioDraft> {
  return unwrap(
    await api.PUT('/api/v1/folio/nodes/{node_id}/draft', {
      params: { path: { node_id: id } },
      body,
    }),
  );
}

/** Publishes (a version) or, for agents, sends for approval (a submission). */
export async function publishNode(
  id: string,
  body: FolioPublishIn,
): Promise<FolioVersion | FolioSubmission> {
  return unwrap(
    await api.POST('/api/v1/folio/nodes/{node_id}/publish', {
      params: { path: { node_id: id } },
      body,
    }),
  );
}

export async function uploadAsset(id: string, file: File): Promise<FolioAsset> {
  const body = new FormData();
  body.append('file', file);
  return unwrap(
    await api.POST('/api/v1/folio/nodes/{node_id}/assets', {
      params: { path: { node_id: id } },
      // openapi-fetch sends FormData as is.
      body: body as never,
    }),
  );
}

export function assetUrl(assetId: string): string {
  return `/api/v1/folio/assets/${assetId}`;
}

// --- history -------------------------------------------------------------------------

export async function fetchVersions(id: string): Promise<FolioVersion[]> {
  return unwrap(
    await api.GET('/api/v1/folio/nodes/{node_id}/versions', { params: { path: { node_id: id } } }),
  ).items;
}

export async function fetchVersion(id: string, number: number): Promise<FolioVersionContent> {
  return unwrap(
    await api.GET('/api/v1/folio/nodes/{node_id}/versions/{number}', {
      params: { path: { node_id: id, number } },
    }),
  );
}

export async function fetchDiff(id: string, from: number, to: number): Promise<FolioDiff> {
  return unwrap(
    await api.GET('/api/v1/folio/nodes/{node_id}/diff', {
      params: { path: { node_id: id }, query: { from, to } },
    }),
  );
}

export async function restoreVersion(id: string, number: number): Promise<FolioVersion> {
  return unwrap(
    await api.POST('/api/v1/folio/nodes/{node_id}/versions/{number}/restore', {
      params: { path: { node_id: id, number } },
      body: {},
    }),
  );
}

/** A live doc's snapshots (Folio 2.5), newest first, with who wrote since the one before. */
export async function fetchSnapshots(id: string): Promise<FolioSnapshot[]> {
  return unwrap(
    await api.GET('/api/v1/folio/nodes/{node_id}/snapshots', { params: { path: { node_id: id } } }),
  ).items;
}

export async function fetchSnapshot(id: string, sid: string): Promise<FolioSnapshotContent> {
  return unwrap(
    await api.GET('/api/v1/folio/nodes/{node_id}/snapshots/{snapshot_id}', {
      params: { path: { node_id: id, snapshot_id: sid } },
    }),
  );
}

/** Brings a live doc back to a snapshot for everyone writing in it; that is a new snapshot. */
export async function restoreSnapshot(id: string, sid: string): Promise<FolioSnapshot> {
  return unwrap(
    await api.POST('/api/v1/folio/nodes/{node_id}/snapshots/{snapshot_id}/restore', {
      params: { path: { node_id: id, snapshot_id: sid } },
    }),
  );
}

// --- approvals -----------------------------------------------------------------------

export async function fetchSubmissions(status?: SubmissionStatus): Promise<FolioSubmission[]> {
  return unwrap(await api.GET('/api/v1/folio/submissions', { params: { query: { status } } }))
    .items;
}

export async function fetchSubmission(id: string): Promise<FolioSubmissionDetail> {
  return unwrap(
    await api.GET('/api/v1/folio/submissions/{submission_id}', {
      params: { path: { submission_id: id } },
    }),
  );
}

export async function approveSubmission(id: string, comment?: string): Promise<FolioVersion> {
  return unwrap(
    await api.POST('/api/v1/folio/submissions/{submission_id}/approve', {
      params: { path: { submission_id: id } },
      body: { comment },
    }),
  );
}

export async function rejectSubmission(id: string, comment: string): Promise<FolioSubmission> {
  return unwrap(
    await api.POST('/api/v1/folio/submissions/{submission_id}/reject', {
      params: { path: { submission_id: id } },
      body: { comment },
    }),
  );
}

// --- metadata and catalogs -----------------------------------------------------------

export async function fetchMetadataSchema(): Promise<FolioSchema> {
  return unwrap(await api.GET('/api/v1/folio/metadata-schema'));
}

export async function fetchCatalog(catalog: FolioCatalog): Promise<FolioEntry[]> {
  return unwrap(await api.GET('/api/v1/folio/admin/{catalog}', { params: { path: { catalog } } }))
    .items;
}

export async function createEntry(catalog: FolioCatalog, body: FolioEntryIn): Promise<FolioEntry> {
  return unwrap(
    await api.POST('/api/v1/folio/admin/{catalog}', { params: { path: { catalog } }, body }),
  );
}

export async function updateEntry(
  catalog: FolioCatalog,
  key: string,
  body: FolioEntryPatch,
): Promise<FolioEntry> {
  return unwrap(
    await api.PATCH('/api/v1/folio/admin/{catalog}/{key}', {
      params: { path: { catalog, key } },
      body,
    }),
  );
}

// --- search and RQL ------------------------------------------------------------------

export type SearchFilters = {
  space?: string;
  kind?: 'page' | 'blog_post';
  doc_type?: string;
  label?: string;
  author?: string;
  owner?: string;
  audience?: string;
  language?: string;
  from?: string;
  to?: string;
};

export async function searchDocs(
  q: string,
  mode: SearchMode = 'hybrid',
  filters: SearchFilters = {},
  limit = 10,
): Promise<FolioSearch> {
  return unwrap(
    await api.GET('/api/v1/folio/search', { params: { query: { q, mode, limit, ...filters } } }),
  );
}

export async function queryDocs(
  q: string,
  limit = 20,
  cursor?: string,
): Promise<{ items: FolioDoc[]; next_cursor?: string | null }> {
  return unwrap(await api.GET('/api/v1/folio/nodes', { params: { query: { q, limit, cursor } } }));
}

// --- home ----------------------------------------------------------------------------

export type FolioHome = S['HomeOut'];
export type FolioCard = S['CardOut'];
export type FolioHomeBlock = S['HomeBlockOut'];
export const folioHomeKey = ['folio', 'home'] as const;

/** The home bento, every block already resolved for you. */
export async function fetchHome(): Promise<FolioHome> {
  return unwrap(await api.GET('/api/v1/folio/home'));
}

// --- templates (Folio 3.1) -----------------------------------------------------------

export async function fetchTemplates(
  kind: 'page' | 'space' = 'page',
  space?: string,
): Promise<FolioTemplate[]> {
  return unwrap(await api.GET('/api/v1/folio/templates', { params: { query: { kind, space } } }))
    .items;
}

export async function fetchTemplate(id: string): Promise<FolioTemplate> {
  return unwrap(
    await api.GET('/api/v1/folio/templates/{template_id}', {
      params: { path: { template_id: id } },
    }),
  );
}

export async function createTemplate(body: FolioTemplateIn): Promise<FolioTemplate> {
  return unwrap(await api.POST('/api/v1/folio/templates', { body }));
}

export async function updateTemplate(id: string, body: FolioTemplatePatch): Promise<FolioTemplate> {
  return unwrap(
    await api.PATCH('/api/v1/folio/templates/{template_id}', {
      params: { path: { template_id: id } },
      body,
    }),
  );
}

export async function archiveTemplate(id: string): Promise<void> {
  unwrap(
    await api.DELETE('/api/v1/folio/templates/{template_id}', {
      params: { path: { template_id: id } },
    }),
  );
}

/** A page or post whose draft starts with the template's document and metadata. */
export async function createFromTemplate(body: NodeFromTemplateIn): Promise<FolioNode> {
  return unwrap(await api.POST('/api/v1/folio/nodes/from-template', { body }));
}

/** A pasted link's card, and an iframe URL for the providers that embed (Folio 3.7). */
export async function fetchLinkPreview(url: string): Promise<FolioLinkPreview> {
  return unwrap(await api.GET('/api/v1/folio/link-preview', { params: { query: { url } } }));
}
