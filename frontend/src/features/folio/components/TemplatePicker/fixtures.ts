/** A page template as the API returns it, for tests. */
export const SPEC = {
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
