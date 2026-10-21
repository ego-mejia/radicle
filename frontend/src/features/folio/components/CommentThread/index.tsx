import { Check, Pencil, RotateCcw, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MarkdownEditor, type MentionOption } from '../../../../components/Markdown/MarkdownEditor';
import { MarkdownView } from '../../../../components/Markdown/MarkdownView';
import { Avatar } from '../../../../components/ui/Avatar';
import { Button } from '../../../../components/ui/Button';
import { relativeTime } from '../../../../lib/format';
import type { FolioComment, FolioThread } from '../../../../services/api/folioComments';
import { CommentReactions } from '../CommentReactions';
import * as S from './style';

type Props = {
  thread: FolioThread;
  mentions: MentionOption[];
  canComment: boolean;
  onReply: (body: string) => Promise<unknown>;
  onEdit: (id: string, body: string) => Promise<unknown>;
  onDelete: (id: string) => void;
  onResolve: (resolved: boolean) => void;
};

function Comment({
  comment,
  mentions,
  onEdit,
  onDelete,
}: {
  comment: FolioComment;
  mentions: MentionOption[];
  onEdit: Props['onEdit'];
  onDelete: Props['onDelete'];
}) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState<string | null>(null);
  const save = async () => {
    if (editing?.trim()) await onEdit(comment.id, editing);
    setEditing(null);
  };
  return (
    <S.Comment id={`comment-${comment.id}`}>
      <S.Head>
        {comment.author && (
          <Avatar handle={comment.author} name={comment.author_name ?? undefined} size={24} />
        )}
        <strong>{comment.author_name ?? t('folio.comments.removed')}</strong>
        <S.When dateTime={comment.created_at}>{relativeTime(comment.created_at)}</S.When>
        {comment.edited_at && <S.When as="span">{t('folio.comments.edited')}</S.When>}
        {comment.mine && editing === null && (
          <S.Tools>
            <S.Icon
              type="button"
              aria-label={t('folio.comments.edit')}
              onClick={() => setEditing(comment.body_md)}
            >
              <Pencil aria-hidden />
            </S.Icon>
            <S.Icon
              type="button"
              aria-label={t('folio.comments.delete')}
              onClick={() => onDelete(comment.id)}
            >
              <Trash2 aria-hidden />
            </S.Icon>
          </S.Tools>
        )}
      </S.Head>
      {editing === null ? (
        <MarkdownView readOnly>{comment.body_md}</MarkdownView>
      ) : (
        <S.Compose>
          <MarkdownEditor
            value={editing}
            onChange={setEditing}
            mentions={mentions}
            onSubmit={() => void save()}
            ariaLabel={t('folio.comments.edit')}
            autoFocus
          />
          <S.Row>
            <Button size="sm" onClick={() => setEditing(null)}>
              {t('folio.comments.cancel')}
            </Button>
            <Button size="sm" variant="primary" onClick={() => void save()}>
              {t('folio.comments.save')}
            </Button>
          </S.Row>
        </S.Compose>
      )}
      <CommentReactions commentId={comment.id} />
    </S.Comment>
  );
}

/** One thread: what it quotes, its comments, a reply box and resolve or reopen. */
export function CommentThread({
  thread,
  mentions,
  canComment,
  onReply,
  onEdit,
  onDelete,
  onResolve,
}: Props) {
  const { t } = useTranslation();
  const [reply, setReply] = useState('');
  const resolved = thread.resolved_at != null;
  const send = async () => {
    if (!reply.trim()) return;
    await onReply(reply);
    setReply('');
  };
  return (
    <S.Thread
      id={`comment-${thread.id}`}
      aria-label={t('folio.comments.thread')}
      $resolved={resolved}
    >
      {thread.anchor && (
        <S.Quote $orphaned={thread.orphaned}>
          {thread.orphaned && <S.Orphan>{t('folio.comments.orphaned')}</S.Orphan>}“
          {thread.anchor.quote}”
        </S.Quote>
      )}
      {thread.comments.map((c) => (
        <Comment key={c.id} comment={c} mentions={mentions} onEdit={onEdit} onDelete={onDelete} />
      ))}
      {resolved && thread.resolved_by && (
        <S.Note>{t('folio.comments.resolvedBy', { handle: thread.resolved_by })}</S.Note>
      )}
      {canComment && !resolved && (
        <S.Compose>
          <MarkdownEditor
            value={reply}
            onChange={setReply}
            mentions={mentions}
            onSubmit={() => void send()}
            placeholder={t('folio.comments.replyPlaceholder')}
            ariaLabel={t('folio.comments.reply')}
          />
          <S.Row>
            <Button size="sm" onClick={() => onResolve(true)}>
              <Check aria-hidden /> {t('folio.comments.resolve')}
            </Button>
            <Button
              size="sm"
              variant="primary"
              disabled={!reply.trim()}
              onClick={() => void send()}
            >
              {t('folio.comments.reply')}
            </Button>
          </S.Row>
        </S.Compose>
      )}
      {canComment && resolved && (
        <S.Row>
          <Button size="sm" onClick={() => onResolve(false)}>
            <RotateCcw aria-hidden /> {t('folio.comments.reopen')}
          </Button>
        </S.Row>
      )}
    </S.Thread>
  );
}
