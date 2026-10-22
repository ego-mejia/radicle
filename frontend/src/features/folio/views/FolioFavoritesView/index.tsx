import { useQuery } from '@tanstack/react-query';
import { createLink } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { fetchFavorites, fetchRecents, socialKeys } from '../../../../services/api/folioSocial';
import * as S from './style';

const RowLink = createLink(S.Row);

/** Favoritos: the spaces and pages you starred, then what you read last. */
export function FolioFavoritesView() {
  const { t } = useTranslation();
  const favorites = useQuery({ queryKey: socialKeys.favorites, queryFn: fetchFavorites });
  const recents = useQuery({ queryKey: socialKeys.recents, queryFn: fetchRecents });
  const spaces = favorites.data?.spaces ?? [];
  const pages = favorites.data?.nodes ?? [];
  const empty = favorites.data && !spaces.length && !pages.length;

  return (
    <>
      <PageTitle title={t('folio.shortcuts.favorites')} subtitle={t('folio.nav.favoritesHint')} />
      {empty && <EmptyState title={t('folio.nav.favoritesEmpty')} />}
      <S.Groups>
        {(spaces.length > 0 || pages.length > 0) && (
          <S.Group aria-label={t('folio.shortcuts.favorites')}>
            {spaces.map((s) => (
              <RowLink key={s.key} to="/folio/s/$key" params={{ key: s.key }}>
                {s.name}
                <small>{t('folio.nav.space')}</small>
              </RowLink>
            ))}
            {pages.map((n) => (
              <RowLink key={n.id} to="/folio/p/$page" params={{ page: `${n.id}-${n.slug}` }}>
                {n.icon && <span aria-hidden>{n.icon}</span>}
                {n.title}
              </RowLink>
            ))}
          </S.Group>
        )}
        {!!recents.data?.length && (
          <S.Group aria-label={t('folio.shortcuts.recents')}>
            <S.Title>{t('folio.shortcuts.recents')}</S.Title>
            {recents.data.map((n) => (
              <RowLink key={n.id} to="/folio/p/$page" params={{ page: `${n.id}-${n.slug}` }}>
                {n.icon && <span aria-hidden>{n.icon}</span>}
                {n.title}
              </RowLink>
            ))}
          </S.Group>
        )}
      </S.Groups>
    </>
  );
}
