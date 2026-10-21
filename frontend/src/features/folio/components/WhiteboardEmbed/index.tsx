import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { Lock, Shapes } from 'lucide-react';
import { Suspense } from 'react';
import { useTranslation } from 'react-i18next';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { isApiError } from '../../../../services/api/client';
import { fetchWhiteboard, whiteboardKeys } from '../../../../services/api/folioWhiteboards';
import type { SceneElement } from '../../whiteboard/sync';
import { LazyWhiteboardBoard } from '../WhiteboardBoard/lazy';
import * as S from './style';

/** A whiteboard inside a page (Folio 3.5): the scene read only, with a link to draw on it.
 * Whoever can't see the whiteboard sees a placeholder instead. */
export function WhiteboardEmbed({ nodeId }: { nodeId: string }) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const board = useQuery({
    queryKey: whiteboardKeys.whiteboard(nodeId),
    queryFn: () => fetchWhiteboard(nodeId),
    retry: false,
  });

  if (board.isError) {
    if (isApiError(board.error, 404))
      return (
        <S.NoAccess role="note">
          <Lock aria-hidden />
          {t('folio.whiteboard.noAccess')}
        </S.NoAccess>
      );
    return <S.Error role="alert">{errorMessage(board.error)}</S.Error>;
  }
  if (!board.data) return <PageSpinner />;
  return (
    <S.Embed>
      <S.Head>
        <Shapes aria-hidden />
        <Link to="/folio/p/$page" params={{ page: board.data.node_id }}>
          {board.data.title}
        </Link>
      </S.Head>
      <S.Canvas>
        <Suspense fallback={<PageSpinner />}>
          <LazyWhiteboardBoard elements={board.data.elements as SceneElement[]} />
        </Suspense>
      </S.Canvas>
    </S.Embed>
  );
}
