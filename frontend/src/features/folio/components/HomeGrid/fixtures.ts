import type { FolioCard, FolioHomeBlock } from '../../../../services/api/folio';

/** Test data for the home's blocks. */
export function card(id: string, title: string, extra: Partial<FolioCard> = {}): FolioCard {
  return {
    id,
    kind: 'blog_post',
    title,
    slug: title.toLowerCase().replace(/ /g, '-'),
    icon: null,
    cover_asset_id: null,
    space: 'eng',
    space_name: 'Ingeniería',
    description: `About ${title}`,
    doc_type: null,
    labels: [],
    author: 'fernando',
    author_name: 'Fernando',
    published_at: '2026-10-20T10:00:00Z',
    reading_minutes: 6,
    status: 'published',
    ...extra,
  };
}

export function block(
  type: string,
  x: number,
  y: number,
  w: number,
  extra: Partial<FolioHomeBlock> = {},
): FolioHomeBlock {
  return {
    id: `${type}-${x}-${y}`,
    type,
    x,
    y,
    w,
    h: 2,
    title: '',
    cards: [],
    spaces: [],
    markdown: '',
    calendar: null,
    view: 'month',
    ...extra,
  };
}
