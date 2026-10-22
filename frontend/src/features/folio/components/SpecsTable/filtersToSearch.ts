import type { SpecFilters } from '../../../../services/api/folioSections';

/** The filters as a query string, so a view can be shared or bookmarked as a link. */
export function filtersToSearch(f: SpecFilters): string {
  const params = new URLSearchParams();
  if (f.project) params.set('project', f.project);
  for (const x of f.features) params.append('feature', x);
  if (f.status) params.set('status', f.status);
  if (f.owner) params.set('owner', f.owner);
  if (f.q) params.set('q', f.q);
  return params.toString();
}
