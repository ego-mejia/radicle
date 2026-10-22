import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { Spinner } from '../../../../components/ui/Spinner';
import { queryDocs } from '../../../../services/api/folio';
import type { SpaceSectionKey } from '../../../../services/api/folioSpaces';
import { sectionQuery } from '../../sections';
import * as S from './style';

type Props = { space: string; section: SpaceSectionKey; q?: string };

/** The published pages of a section, newest first; a text filter narrows them by title. */
export function SectionDocs({ space, section, q = '' }: Props) {
  const { t, i18n } = useTranslation();
  const text = q.trim().replace(/"/g, '');
  const rql = sectionQuery(space, section, text ? `title ~ "${text}"` : '');
  const docs = useQuery({
    queryKey: ['folio', 'section', space, section, text],
    queryFn: () => queryDocs(rql, 50),
  });
  if (docs.isPending) return <Spinner />;
  if (docs.isError)
    return <EmptyState title={t('folio.sectionDocs.error')} text={docs.error.message} />;
  if (!docs.data.items.length)
    return (
      <EmptyState
        title={text ? t('folio.sectionDocs.noMatch', { q: text }) : t('folio.sectionDocs.empty')}
        text={t('folio.sectionDocs.emptyHint')}
      />
    );
  const date = new Intl.DateTimeFormat(i18n.language, { day: 'numeric', month: 'short' });
  return (
    <S.List>
      {docs.data.items.map((doc) => {
        const meta = (doc.metadata ?? {}) as { description?: string; owner?: string };
        return (
          <li key={doc.id}>
            <S.Card to={`/folio/p/${doc.id}-${doc.slug}`}>
              <b>{doc.title}</b>
              {meta.description && <span>{meta.description}</span>}
              <small>
                {[meta.owner, doc.published_at && date.format(new Date(doc.published_at))]
                  .filter(Boolean)
                  .join(' · ')}
              </small>
            </S.Card>
          </li>
        );
      })}
    </S.List>
  );
}
