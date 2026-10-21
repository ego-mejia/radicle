import { createLink } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import type { FolioHome } from '../../../../../../services/api/folio';
import * as S from './style';

const ItemLink = createLink(S.Item);

type Props = { title: string; spaces: FolioHome['spaces'] };

/** The spaces you can see, with how many docs each has. */
export function SpaceList({ title, spaces }: Props) {
  const { t } = useTranslation();
  return (
    <S.Section aria-label={title}>
      <S.Heading>{title}</S.Heading>
      {spaces.length === 0 ? (
        <S.Empty>{t('folio.home.noSpaces')}</S.Empty>
      ) : (
        <S.List>
          {spaces.map((space) => (
            <li key={space.key}>
              <ItemLink to="/folio/s/$key" params={{ key: space.key }}>
                <S.Letter aria-hidden>{space.icon ?? space.name.charAt(0).toUpperCase()}</S.Letter>
                <S.Name>{space.name}</S.Name>
                <S.Count>{t('folio.home.docs', { count: space.docs })}</S.Count>
              </ItemLink>
            </li>
          ))}
        </S.List>
      )}
    </S.Section>
  );
}
