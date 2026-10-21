import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../../../hooks/useErrorMessage';
import { type HomeLayoutBlock, previewHome } from '../../../../../../services/api/folio';
import { HomeGrid } from '../../../HomeGrid';
import * as S from './style';

/** The layout being edited, saved or not, drawn the way the home draws it (ADR 0041). */
export function HomePreview({ blocks }: { blocks: HomeLayoutBlock[] }) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const preview = useQuery({
    queryKey: ['folio', 'home', 'preview', blocks],
    queryFn: () => previewHome({ columns: 12, blocks }),
    retry: false,
  });
  return (
    <S.Wrap aria-label={t('folio.homeEditor.preview')}>
      <S.Note>{t('folio.homeEditor.previewNote')}</S.Note>
      {preview.isPending ? (
        <PageSpinner />
      ) : preview.isError ? (
        <S.Problem role="alert">{errorMessage(preview.error)}</S.Problem>
      ) : preview.data.length === 0 ? (
        <EmptyState plant="seed" title={t('folio.homeEditor.previewEmpty')} />
      ) : (
        <HomeGrid blocks={preview.data} />
      )}
    </S.Wrap>
  );
}
