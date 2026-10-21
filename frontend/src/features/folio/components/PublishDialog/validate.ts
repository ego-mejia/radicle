// The publishing rules of backend/radicle/folio/services/metadata.py, checked while you type.
// The server checks them again; its 422 errors show on the same fields.

export type Metadata = {
  description: string;
  doc_type: string;
  labels: string[];
  owner: string;
  audiences: string[];
  language: string;
};

export type Field = keyof Metadata | 'title';
export type Problems = Partial<Record<Field, string>>;

const LABEL = /^[a-z0-9][a-z0-9_-]{0,49}$/;
const SENTENCE_END = /[.!?…](?:\s|$)/g;

/** `#Onboarding, mcp` → `['onboarding', 'mcp']`, without repeats. */
export function parseLabels(text: string): string[] {
  const labels = text
    .split(/[,\s]+/)
    .map((label) => label.trim().toLowerCase().replace(/^#/, ''))
    .filter(Boolean);
  return [...new Set(labels)];
}

/** The fields that would fail, each with the i18n key of its rule. */
export function validate(title: string, m: Metadata, catalogs: Record<string, string[]>) {
  const problems: Problems = {};
  if (!title.trim() || title.trim().length > 200) problems.title = 'rules.title';
  const description = m.description.trim();
  if (description.length < 40 || description.length > 400) {
    problems.description = 'rules.descriptionLength';
  } else if (Math.max(1, description.match(SENTENCE_END)?.length ?? 0) > 3) {
    problems.description = 'rules.descriptionSentences';
  }
  if (!catalogs.doc_types?.includes(m.doc_type)) problems.doc_type = 'rules.docType';
  if (!m.labels.length || m.labels.length > 15) problems.labels = 'rules.labelsCount';
  else if (m.labels.some((label) => !LABEL.test(label))) problems.labels = 'rules.labelsFormat';
  if (!m.owner.trim()) problems.owner = 'rules.owner';
  if (!m.audiences.length || m.audiences.some((a) => !catalogs.audiences?.includes(a))) {
    problems.audiences = 'rules.audiences';
  }
  if (!catalogs.languages?.includes(m.language)) problems.language = 'rules.language';
  return problems;
}

/** The draft's metadata as the form edits it; missing pieces start empty. */
export function fromDraft(raw: Record<string, unknown>, owner: string): Metadata {
  const list = (value: unknown) => (Array.isArray(value) ? value.map(String) : []);
  const text = (value: unknown) => (typeof value === 'string' ? value : '');
  return {
    description: text(raw.description),
    doc_type: text(raw.doc_type),
    labels: list(raw.labels),
    owner: text(raw.owner).replace(/^@/, '') || owner,
    audiences: list(raw.audiences),
    language: text(raw.language),
  };
}
