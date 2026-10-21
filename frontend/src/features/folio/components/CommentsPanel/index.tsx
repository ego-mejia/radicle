import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MarkdownEditor } from '../../../../components/Markdown/MarkdownEditor';
import { Button } from '../../../../components/ui/Button';
import { Spinner } from '../../../../components/ui/Spinner';
import { useComments } from '../../hooks/useComments';
import { CommentThread } from '../CommentThread';
import { type CommentFilter, FILTERS, inFilter } from './filters';
import * as S from './style';

type Props = { nodeId: string; canComment: boolean };

/** The page's discussion: open, resolved and orphaned threads, and a new comment box. */
export function CommentsPanel({ nodeId, canComment }: Props) {
  const { t } = useTranslation();
  const { threads, mentions, add, edit, remove, resolve } = useComments(nodeId);
  const [filter, setFilter] = useState<CommentFilter>('open');
  const [draft, setDraft] = useState('');
  const all = threads.data ?? [];
  const shown = all.filter((th) => inFilter(th, filter));

  const post = async () => {
    if (!draft.trim()) return;
    await add.mutateAsync({ body: draft });
    setDraft('');
  };

  return (
    <S.Panel aria-label={t('folio.comments.title')}>
      <S.Header>
        <h2>{t('folio.comments.title')}</h2>
        <S.Filters role="tablist" aria-label={t('folio.comments.filter')}>
          {FILTERS.map((f) => (
            <S.Filter
              key={f}
              type="button"
              role="tab"
              aria-selected={filter === f}
              $on={filter === f}
              onClick={() => setFilter(f)}
            >
              {t(`folio.comments.filters.${f}`)}{' '}
              <S.Count>{all.filter((th) => inFilter(th, f)).length}</S.Count>
            </S.Filter>
          ))}
        </S.Filters>
      </S.Header>

      {canComment && filter === 'open' && (
        <S.Compose>
          <MarkdownEditor
            value={draft}
            onChange={setDraft}
            mentions={mentions}
            onSubmit={() => void post()}
            placeholder={t('folio.comments.placeholder')}
            ariaLabel={t('folio.comments.new')}
          />
          <Button
            size="sm"
            variant="primary"
            disabled={!draft.trim() || add.isPending}
            onClick={() => void post()}
          >
            {t('folio.comments.post')}
          </Button>
        </S.Compose>
      )}

      {threads.isPending ? (
        <Spinner />
      ) : shown.length === 0 ? (
        <S.Empty>{t(`folio.comments.empty.${filter}`)}</S.Empty>
      ) : (
        shown.map((thread) => (
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
        ))
      )}
    </S.Panel>
  );
}
