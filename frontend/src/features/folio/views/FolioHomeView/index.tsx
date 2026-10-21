import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { fetchHome, folioHomeKey } from '../../../../services/api/folio';
import { Featured } from './components/Featured';
import { Spotlight } from './components/Spotlight';
import * as S from './style';

/** Folio's home (Folio 1.8): the default bento, every block resolved by GET /home. */
export function FolioHomeView() {
  const { t } = useTranslation();
  const { data: home } = useQuery({ queryKey: folioHomeKey, queryFn: fetchHome });
  if (!home) return <PageSpinner />;
  const empty = !home.featured && home.latest_posts.length === 0 && home.most_read.length === 0;

  return (
    <S.Wrap>
      <S.Top>
        <S.Heading>{t('folio.home.title')}</S.Heading>
      </S.Top>
      {empty ? (
        <EmptyState
          plant="seed"
          title={t('folio.home.emptyTitle')}
          text={t(home.can_write ? 'folio.home.emptyWriter' : 'folio.home.emptyReader')}
        />
      ) : (
        <>
          <S.Row>
            <S.Column $grow={7} $basis={540}>
              {home.featured && <Featured doc={home.featured} />}
            </S.Column>
            <S.Column $grow={5} $basis={360}>
              {home.announcement && (
                <Spotlight
                  tone="accent"
                  label={t('folio.home.announcement')}
                  doc={home.announcement}
                />
              )}
              {home.ai_tools[0] && (
                <Spotlight tone="plain" label={t('folio.home.aiTools')} doc={home.ai_tools[0]} />
              )}
            </S.Column>
          </S.Row>
        </>
      )}
    </S.Wrap>
  );
}
