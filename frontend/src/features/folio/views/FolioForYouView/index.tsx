import { useQuery } from '@tanstack/react-query';
import { createLink } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { fetchFeed, socialKeys } from '../../../../services/api/folioSocial';
import * as S from './style';

const ItemLink = createLink(S.Item);
const LIMIT = 30;

/** Para ti: what the people and spaces you follow published, then the week's most read. */
export function FolioForYouView() {
  const { t } = useTranslation();
  const { data: items } = useQuery({
    queryKey: [...socialKeys.feed, LIMIT],
    queryFn: () => fetchFeed(LIMIT),
  });
  return (
    <>
      <PageTitle title={t('folio.nav.forYou')} subtitle={t('folio.nav.forYouHint')} />
      {items && !items.length && <EmptyState title={t('folio.nav.forYouEmpty')} />}
      <S.List>
        {(items ?? []).map((item) => (
          <li key={item.id}>
            <ItemLink to="/folio/p/$page" params={{ page: `${item.id}-${item.slug}` }}>
              <S.Kicker>{[item.doc_type, item.space_name].filter(Boolean).join(' · ')}</S.Kicker>
              <b>{item.title}</b>
              {item.description && <span>{item.description}</span>}
              <small>
                {[item.author_name, t('folio.reader.minutes', { count: item.reading_minutes })]
                  .filter(Boolean)
                  .join(' · ')}
              </small>
            </ItemLink>
          </li>
        ))}
      </S.List>
    </>
  );
}
