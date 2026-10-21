import { useTranslation } from 'react-i18next';
import { useComments } from '../../hooks/useComments';
import { CommentThread } from '../CommentThread';
import * as S from './style';

type Props = { nodeId: string; canComment: boolean };

/** Focus mode's margin: the open inline threads, next to the text they talk about. */
export function MarginComments({ nodeId, canComment }: Props) {
  const { t } = useTranslation();
  const { threads, mentions, add, edit, remove, resolve } = useComments(nodeId);
  const inline = (threads.data ?? []).filter(
    (th) => th.kind === 'inline' && !th.orphaned && th.resolved_at == null,
  );
  if (inline.length === 0) return null;
  return (
    <S.Margin aria-label={t('folio.comments.margin')}>
      {inline.map((thread) => (
        <CommentThread
          key={thread.id}
          thread={thread}
          mentions={mentions}
          canComment={canComment}
          onReply={(body) => add.mutateAsync({ body, thread_id: thread.id })}
          onEdit={(id, body) => edit.mutateAsync({ id, body })}
          onDelete={(id) => remove.mutate(id)}
          onResolve={(resolved) => resolve.mutate({ id: thread.id, resolved })}
        />
      ))}
    </S.Margin>
  );
}
