import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { fetchHome, folioHomeKey } from '../../../../services/api/folio';
import { HomeGrid } from '../../components/HomeGrid';
import * as S from './style';

/** Folio's home: the published layout (Folio 3.2), every block resolved by GET /home. */
export function FolioHomeView() {
  const { t } = useTranslation();
  const { data: home } = useQuery({ queryKey: folioHomeKey, queryFn: fetchHome });
  if (!home) return <PageSpinner />;
  const empty = !home.blocks.some((b) => b.cards.length > 0 || b.type === 'text');

  return (
    <S.Wrap>
      <S.Top>
        <S.Heading>{t('folio.home.title')}</S.Heading>
      </S.Top>
      {empty && (
        <EmptyState
          plant="seed"
          title={t('folio.home.emptyTitle')}
          text={t(home.can_write ? 'folio.home.emptyWriter' : 'folio.home.emptyReader')}
        />
      )}
      {home.blocks.length > 0 && <HomeGrid blocks={home.blocks} />}
    </S.Wrap>
  );
}
