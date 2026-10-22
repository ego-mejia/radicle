import { useQuery } from '@tanstack/react-query';
import { useParams } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { fetchSpace, folioKeys } from '../../../../services/api/folio';
import { NewNodeDialog } from '../../components/NewNodeDialog';
import { SpaceHero } from '../../components/SpaceHero';
import { SpacePortada } from '../../components/SpacePortada';
import * as S from '../FolioSectionView/style';

/** A space (RAD-57): its dark hero and its portada in bento. "Manage" holds the tree. */
export function FolioSpaceView() {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const { key } = useParams({ from: '/folio/folio/s/$key' });
  const [writing, setWriting] = useState(false);
  const space = useQuery({ queryKey: folioKeys.space(key), queryFn: () => fetchSpace(key) });
  if (space.isPending) return <PageSpinner />;
  if (space.isError)
    return <EmptyState title={t('folio.space.notFound')} text={errorMessage(space.error)} />;
  const canCreate = space.data.permissions.includes('create');
  return (
    <>
      <SpaceHero
        space={space.data}
        active="all"
        onWrite={canCreate ? () => setWriting(true) : undefined}
      />
      <S.Body>
        <SpacePortada space={key} />
      </S.Body>
      {writing && (
        <NewNodeDialog space={key} kind="page" open onOpenChange={(open) => setWriting(open)} />
      )}
    </>
  );
}
