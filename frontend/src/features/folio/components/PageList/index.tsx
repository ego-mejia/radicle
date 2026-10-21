import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { fetchPageList, folioKeys, type PageListQuery } from '../../../../services/api/folio';
import * as S from './style';

/** The "list by label" block (Folio 3.4): the published pages with a label, resolved on
 * the server with what the reader may see. An empty list says so instead of hiding. */
export function PageList(query: PageListQuery) {
  const { t } = useTranslation();
  const { data, isError } = useQuery({
    queryKey: folioKeys.pageList(query),
    queryFn: () => fetchPageList(query),
    staleTime: 60 * 1000,
  });
  return (
    <S.Box aria-label={t('folio.reader.pageList', { label: query.label })}>
      <S.Label>#{query.label}</S.Label>
      {isError ? (
        <S.Muted>{t('folio.reader.pageListFailed')}</S.Muted>
      ) : data && !data.length ? (
        <S.Muted>{t('folio.reader.pageListEmpty')}</S.Muted>
      ) : (
        <ul aria-busy={!data}>
          {(data ?? []).map((page) => (
            <li key={page.id}>
              <Link to="/folio/p/$page" params={{ page: `${page.id}-${page.slug}` }}>
                {page.title}
              </Link>
              <S.Muted as="span">{page.space}</S.Muted>
            </li>
          ))}
        </ul>
      )}
    </S.Box>
  );
}
