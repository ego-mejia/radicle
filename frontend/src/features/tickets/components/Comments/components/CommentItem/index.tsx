import { MoreHorizontal, Pencil, SmilePlus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  MarkdownEditor,
  type MentionOption,
} from '../../../../../../components/Markdown/MarkdownEditor';
import { MarkdownView } from '../../../../../../components/Markdown/MarkdownView';
import { Avatar } from '../../../../../../components/ui/Avatar';
import { Button, IconButton } from '../../../../../../components/ui/Button';
import { Menu } from '../../../../../../components/ui/Menu';
import { formatDateTime, relativeTime } from '../../../../../../lib/format';
import type { Comment } from '../../../../../../services/api/types';
import * as S from './style';

const QUICK_REACTIONS = ['👍', '🎉', '❤️', '👀', '🌱'];

type Props = {
  comment: Comment;
  me: string;
  canReact: boolean;
  canModerate: boolean;
  mentions: MentionOption[];
  onEdit: (body: string) => Promise<unknown>;
  onDelete: () => void;
  onReact: (emoji: string, on: boolean) => void;
};

export function CommentItem({
  comment,
  me,
  canReact,
  canModerate,
  mentions,
  onEdit,
  onDelete,
  onReact,
}: Props) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<string | null>(null);
  const mine = comment.author.handle === me;
  const author = comment.author;

  const save = async () => {
    if (draft === null) return;
    await onEdit(draft);
    setDraft(null);
  };

  return (
    <S.Item>
      <Avatar handle={author.handle} name={author.display_name} kind={author.kind} size={28} />
      <S.Bubble $deleted={comment.deleted}>
        <S.Meta>
          <strong>{author.display_name}</strong>
          <span title={formatDateTime(comment.created_at)}>{relativeTime(comment.created_at)}</span>
          {comment.edited_at && !comment.deleted && <span>· {t('comments.edited')}</span>}
          <S.Spacer />
          {!comment.deleted && canReact && (
            <Menu
              align="end"
              trigger={
                <IconButton label={t('comments.react')}>
                  <SmilePlus />
                </IconButton>
              }
              items={QUICK_REACTIONS.map((emoji) => ({
                key: emoji,
                label: emoji,
                onSelect: () => onReact(emoji, true),
              }))}
            />
          )}
          {!comment.deleted && (mine || canModerate) && (
            <Menu
              align="end"
              trigger={
                <IconButton label={t('common.more')}>
                  <MoreHorizontal />
                </IconButton>
              }
              items={[
                ...(mine
                  ? [
                      {
                        key: 'edit',
                        label: t('common.edit'),
                        icon: <Pencil />,
                        onSelect: () => setDraft(comment.body_md),
                      },
                    ]
                  : []),
                {
                  key: 'delete',
                  label: t('common.delete'),
                  icon: <Trash2 />,
                  danger: true,
                  onSelect: onDelete,
                },
              ]}
            />
          )}
        </S.Meta>
        {comment.deleted ? (
          <S.Deleted>{t('comments.deleted')}</S.Deleted>
        ) : draft !== null ? (
          <>
            <MarkdownEditor
              value={draft}
              onChange={setDraft}
              mentions={mentions}
              autoFocus
              onSubmit={() => void save()}
              ariaLabel={t('common.edit')}
            />
            <S.EditActions>
              <Button size="sm" variant="primary" onClick={() => void save()}>
                {t('common.save')}
              </Button>
              <Button size="sm" onClick={() => setDraft(null)}>
                {t('common.cancel')}
              </Button>
            </S.EditActions>
          </>
        ) : (
          <MarkdownView readOnly>{comment.body_md}</MarkdownView>
        )}
        {!comment.deleted && (comment.reactions ?? []).length > 0 && (
          <S.Reactions>
            {(comment.reactions ?? []).map((r) => {
              const reacted = r.users.includes(me);
              return (
                <S.Reaction
                  key={r.emoji}
                  $mine={reacted}
                  disabled={!canReact}
                  title={r.users.map((u) => `@${u}`).join(', ')}
                  aria-pressed={reacted}
                  onClick={() => onReact(r.emoji, !reacted)}
                >
                  {r.emoji} {r.count}
                </S.Reaction>
              );
            })}
          </S.Reactions>
        )}
      </S.Bubble>
    </S.Item>
  );
}
