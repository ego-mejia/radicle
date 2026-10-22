import type { SpaceSectionKey } from '../../services/api/folioSpaces';

/** Where each section of a space lives and which doc types its pages have (RAD-57). The
 * labels come from i18n: `folio.sections.<key>.*`. */
export const SECTIONS: Record<SpaceSectionKey, { path: string; docTypes: string[] }> = {
  specs: { path: 'specs', docTypes: ['build-spec'] },
  decisions: { path: 'decisions', docTypes: ['decision-log'] },
  guides: { path: 'guides', docTypes: ['how-to', 'guide'] },
  docs: { path: 'docs', docTypes: ['reference'] },
};

/** The RQL that lists a section's published pages in a space, newest first. */
export function sectionQuery(
  space: string,
  key: SpaceSectionKey,
  extra = '',
  order = 'published DESC',
): string {
  const types = SECTIONS[key].docTypes.join(', ');
  return `space = ${space} AND doc_type in (${types})${extra ? ` AND ${extra}` : ''} ORDER BY ${order}`;
}

/** The section a page belongs to, by its doc type; undefined when none shows it. */
export function sectionFor(docType: unknown): SpaceSectionKey | undefined {
  if (typeof docType !== 'string') return undefined;
  const keys = Object.keys(SECTIONS) as SpaceSectionKey[];
  return keys.find((k) => SECTIONS[k].docTypes.includes(docType));
}
