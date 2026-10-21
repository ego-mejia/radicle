import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { Clock, Star } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fetchFavorites, fetchRecents, socialKeys } from '../../../../services/api/folioSocial';
import * as S from './style';

const RECENTS = 5;

/** What you read last and what you starred, above a space's tree. */
export function MyShortcuts() {
  const { t } = useTranslation();
  const recents = useQuery({ queryKey: socialKeys.recents, queryFn: fetchRecents });
  const favorites = useQuery({ queryKey: socialKeys.favorites, queryFn: fetchFavorites });
  const recent = (recents.data ?? []).slice(0, RECENTS);
  const starredPages = favorites.data?.nodes ?? [];
  const starredSpaces = favorites.data?.spaces ?? [];
  if (!recent.length && !starredPages.length && !starredSpaces.length) return null;

  return (
    <S.Wrap>
      {(starredPages.length > 0 || starredSpaces.length > 0) && (
        <S.Group aria-label={t('folio.shortcuts.favorites')}>
          <S.Title>
            <Star aria-hidden />
            {t('folio.shortcuts.favorites')}
          </S.Title>
          <S.List>
            {starredSpaces.map((s) => (
              <li key={s.key}>
                <Link to="/folio/s/$key" params={{ key: s.key }}>
                  {s.name}
                </Link>
              </li>
            ))}
            {starredPages.map((n) => (
              <li key={n.id}>
                <Link to="/folio/p/$page" params={{ page: `${n.id}-${n.slug}` }}>
                  {n.icon && <span aria-hidden>{n.icon} </span>}
                  {n.title}
                </Link>
              </li>
            ))}
          </S.List>
        </S.Group>
      )}
      {recent.length > 0 && (
        <S.Group aria-label={t('folio.shortcuts.recents')}>
          <S.Title>
            <Clock aria-hidden />
            {t('folio.shortcuts.recents')}
          </S.Title>
          <S.List>
            {recent.map((n) => (
              <li key={n.id}>
                <Link to="/folio/p/$page" params={{ page: `${n.id}-${n.slug}` }}>
                  {n.icon && <span aria-hidden>{n.icon} </span>}
                  {n.title}
                </Link>
              </li>
            ))}
          </S.List>
        </S.Group>
      )}
    </S.Wrap>
  );
}
