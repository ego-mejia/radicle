import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  type EditorApi,
  MarkdownEditor,
  type MentionOption,
} from '../../../../components/Markdown/MarkdownEditor';
import { Button } from '../../../../components/ui/Button';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import * as api from '../../../../services/api/comments';
import { ticketKeys } from '../../../../services/api/tickets';
import type { Ticket } from '../../../../services/api/types';
import { useUploads } from '../../hooks/useUploads';
import { UploadStatus } from '../UploadStatus';
import { CommentItem } from './components/CommentItem';
import * as S from './style';

type Props = {
  ticket: Ticket;
  me: string;
  canComment: boolean;
  canModerate: boolean;
  mentions: MentionOption[];
};

export function Comments({ ticket, me, canComment, canModerate, mentions }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState('');
  const editor = useRef<EditorApi | null>(null);
  const uploads = useUploads(ticket.key, editor);
  const [deleting, setDeleting] = useState<string | null>(null);
  const key = ticketKeys.comments(ticket.key);
  const { data: comments, isPending } = useQuery({
    queryKey: key,
    queryFn: () => api.fetchComments(ticket.key),
  });

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: key });
    void queryClient.invalidateQueries({ queryKey: ticketKeys.detail(ticket.key) });
    void queryClient.invalidateQueries({ queryKey: ticketKeys.history(ticket.key) });
  };
  const onError = (error: unknown) => toast(errorMessage(error), 'error');
  const add = useMutation({
    mutationFn: () => api.addComment(ticket.key, draft),
    onSuccess: () => {
      setDraft('');
      refresh();
    },
    onError,
  });
  const edit = useMutation({
    mutationFn: (v: { id: string; body: string }) => api.editComment(v.id, v.body),
    onSuccess: refresh,
    onError,
  });
  const remove = useMutation({ mutationFn: api.deleteComment, onSuccess: refresh, onError });
  const react = useMutation({
    mutationFn: (v: { id: string; emoji: string; on: boolean }) =>
      api.setReaction(v.id, v.emoji, v.on),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: key }),
    onError,
  });

  if (isPending) return <PageSpinner />;

  return (
    <S.List>
      {comments?.length === 0 && <S.Empty>{t('comments.empty')}</S.Empty>}
      {comments?.map((comment) => (
        <CommentItem
          key={comment.id}
          comment={comment}
          me={me}
          canReact={canComment}
          canModerate={canModerate}
          mentions={mentions}
          onEdit={(body) => edit.mutateAsync({ id: comment.id, body })}
          onDelete={() => setDeleting(comment.id)}
          onReact={(emoji, on) => react.mutate({ id: comment.id, emoji, on })}
        />
      ))}
      {canComment && (
        <S.Composer>
          <MarkdownEditor
            value={draft}
            onChange={setDraft}
            mentions={mentions}
            placeholder={t('comments.placeholder')}
            onSubmit={() => draft.trim() && add.mutate()}
            ariaLabel={t('comments.placeholder')}
            onFiles={uploads.handleFiles}
            apiRef={editor}
          />
          <UploadStatus uploads={uploads} />
          <Button
            variant="primary"
            disabled={!draft.trim() || add.isPending}
            onClick={() => add.mutate()}
          >
            {t('comments.send')}
          </Button>
        </S.Composer>
      )}
      <ConfirmDialog
        open={deleting !== null}
        title={t('common.delete')}
        message={t('comments.deleteConfirm')}
        confirmLabel={t('common.delete')}
        onCancel={() => setDeleting(null)}
        onConfirm={() => {
          if (deleting) remove.mutate(deleting);
          setDeleting(null);
        }}
      />
    </S.List>
  );
}
