import type { FolioTemplate } from '../../../../services/api/folio';

/** A page template as the API returns it, for tests. */
export const SPEC: FolioTemplate = {
  id: 't1',
  kind: 'page',
  scope: 'global',
  space: null,
  builtin: true,
  name: 'Build spec',
  description: 'Una etapa de trabajo.',
  icon: '🧱',
  doc_type_key: 'build-spec',
  content_json: {
    type: 'doc',
    content: [
      { type: 'heading', attrs: { level: 2 }, content: [{ type: 'text', text: 'Entregables' }] },
    ],
  },
  default_metadata: {},
  structure: null,
  updated_at: '2026-10-21T10:00:00Z',
};

/** A space template with a folder and a page in it, for tests. */
export const ENGINEERING: FolioTemplate = {
  ...SPEC,
  id: 't2',
  kind: 'space',
  builtin: false,
  name: 'Ingeniería',
  description: 'Specs y decisiones.',
  icon: null,
  doc_type_key: null,
  content_json: null,
  structure: {
    pages: [{ title: 'Specs', kind: 'folder', children: [{ title: 'Etapa 1', kind: 'page' }] }],
  },
};
