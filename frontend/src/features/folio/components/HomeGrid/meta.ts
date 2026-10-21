import type { TFunction } from 'i18next';
import { relativeTime } from '../../../../lib/format';
import type { FolioCard } from '../../../../services/api/folio';

/** Route params to read a card's doc: `/folio/p/<id>-<slug>`. */
export function pageParams(doc: FolioCard) {
  return { page: `${doc.id}-${doc.slug}` };
}

/** "Fernando · AI Tools · 6 min read". */
export function cardMeta(t: TFunction, doc: FolioCard, withWhen = false): string {
  const parts = [doc.author_name ?? doc.author, doc.space_name];
  if (withWhen && doc.published_at) parts.push(relativeTime(doc.published_at));
  else parts.push(t('folio.home.minutes', { count: doc.reading_minutes }));
  return parts.filter(Boolean).join(' · ');
}

/** The small mono label over a title: its document type, or "Blog post". */
export function kindLabel(t: TFunction, doc: FolioCard): string {
  return doc.doc_type ?? t(`folio.home.kinds.${doc.kind}`);
}
