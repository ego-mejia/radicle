import { Link, Navigate } from '@tanstack/react-router';
import { Glasses, History, MessageSquare, PenLine } from 'lucide-react';
import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Avatar } from '../../../../components/ui/Avatar';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useMe } from '../../../../hooks/useMe';
import { formatDate } from '../../../../lib/format';
import { assetUrl } from '../../../../services/api/folio';
import { useCommentHighlights } from '../../hooks/useCommentHighlights';
import { useComments } from '../../hooks/useComments';
import { useFocusMode } from '../../hooks/useFocusMode';
import { CommentsPanel } from '../CommentsPanel';
import { DatabasePage } from '../DatabasePage';
import { DocContent } from '../DocContent';
import { headingsOf, readingMinutes } from '../DocContent/anchors';
import { FocusReader } from '../FocusReader';
import { MarginComments } from '../MarginComments';
import { NodeMenu } from '../NodeMenu';
import { PageMeta } from '../PageMeta';
import { PageQuality } from '../PageQuality';
import { PageSocial } from '../PageSocial';
import { PageToc } from '../PageToc';
import { RootsArt } from '../RootsArt';
import { SelectionComment } from '../SelectionComment';
import * as S from './style';
import { usePage } from '../../hooks/usePage';

/** Reading a page in the magazine view: cover, title, lead, byline, content and index. */
export function ReadPage({ nodeId }: { nodeId: string }) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const page = usePage(nodeId);
  const me = useMe();
  const [focus, setFocus] = useFocusMode(me.handle);
  const [comments, setComments] = useState(false);
  const content = useRef<HTMLDivElement>(null);
  const discussion = useComments(nodeId);
  useCommentHighlights(content, discussion.threads.data, [page.content, focus]);
  const { node } = page;

  if (node.isPending) return <PageSpinner />;
  if (node.isError)
    return <EmptyState title={t('folio.reader.unavailable')} text={errorMessage(node.error)} />;
  // A live doc is always open for writing: those who can edit go straight in.
  if (node.data.kind === 'live_doc' && page.canEdit)
    return (
      <Navigate
        to="/folio/p/$page/edit"
        params={{ page: `${node.data.id}-${node.data.slug}` }}
        replace
      />
    );
  if (node.data.kind === 'database')
    return <DatabasePage node={node.data} spaceName={page.space?.name} />;
  if (page.isDraft && page.draft.isPending) return <PageSpinner />;
  if (page.isDraft && page.draft.isError)
    return (
      <EmptyState title={t('folio.reader.notPublished')} text={errorMessage(page.draft.error)} />
    );

  const n = node.data;
  const meta = page.metadata ?? {};
  const owner = meta.owner ? String(meta.owner) : null;
  const description = meta.description ? String(meta.description) : '';
  const params = { page: `${n.id}-${n.slug}` };
  const canComment = !!page.space?.permissions.includes('comment');

  if (focus)
    return (
      <FocusReader
        title={n.title}
        kicker={[meta.doc_type, page.space?.name].filter(Boolean).join(' · ')}
        description={description}
        content={page.content}
        childPages={page.children}
        onExit={() => setFocus(false)}
        contentRef={content}
        margin={
          <>
            <MarginComments nodeId={n.id} canComment={canComment} />
            {canComment && (
              <SelectionComment
                container={content}
                mentions={discussion.mentions}
                onComment={(anchor, body) => discussion.add.mutateAsync({ body, anchor })}
              />
            )}
          </>
        }
      />
    );

  return (
    <S.Page>
      <S.Bar>
        <S.Crumbs aria-label={t('folio.reader.path')}>
          <Link to="/folio/s/$key" params={{ key: n.space }}>
            {page.space?.name ?? n.space}
          </Link>
          {n.breadcrumbs.map((b) => (
            <span key={b.id}>
              <span aria-hidden>/</span>
              <Link to="/folio/p/$page" params={{ page: `${b.id}-${b.slug}` }}>
                {b.title}
              </Link>
            </span>
          ))}
        </S.Crumbs>
        <S.Actions>
          <button type="button" aria-pressed={comments} onClick={() => setComments(!comments)}>
            <MessageSquare aria-hidden />
            {t('folio.comments.title')}
          </button>
          <button type="button" onClick={() => setFocus(true)}>
            <Glasses aria-hidden />
            {t('folio.reader.focus.enter')}
          </button>
          {page.canEdit && n.version != null && (
            <Link to="/folio/p/$page/history" params={params}>
              <History aria-hidden />
              {t('folio.reader.history')}
            </Link>
          )}
          {page.canEdit && (
            <Link to="/folio/p/$page/edit" params={params}>
              <PenLine aria-hidden />
              {t('folio.reader.edit')}
            </Link>
          )}
          {n.can_edit && <NodeMenu node={n} />}
        </S.Actions>
      </S.Bar>

      <S.Cover $image={n.cover_asset_id ? assetUrl(n.cover_asset_id) : null} aria-hidden>
        {!n.cover_asset_id && <RootsArt />}
      </S.Cover>

      <S.Layout>
        <S.Article>
          {page.isDraft && <S.DraftNote role="note">{t('folio.reader.draftNote')}</S.DraftNote>}
          {meta.doc_type ? <S.Tag>{String(meta.doc_type)}</S.Tag> : null}
          <S.Title>
            {n.icon && <span aria-hidden>{n.icon} </span>}
            {n.title}
          </S.Title>
          {description && <S.Lead>{description}</S.Lead>}
          <S.Byline>
            {owner && <Avatar handle={owner} size={36} />}
            <span>
              {owner && <strong>@{owner}</strong>}
              {n.published_at && <> · {formatDate(n.published_at.slice(0, 10))}</>}
              {' · '}
              {t('folio.reader.minutes', { count: readingMinutes(page.content) })}
              {page.author && page.author !== owner && (
                <> · {t('folio.reader.publishedBy', { handle: page.author })}</>
              )}
            </span>
          </S.Byline>
          {n.version != null && <PageSocial nodeId={n.id} title={n.title} />}
          <div ref={content}>
            <DocContent doc={page.content} childPages={page.children} size="large" />
          </div>
          {page.space?.permissions.includes('comment') && (
            <SelectionComment
              container={content}
              mentions={discussion.mentions}
              onComment={async (anchor, body) => {
                await discussion.add.mutateAsync({ body, anchor });
                setComments(true);
              }}
            />
          )}
        </S.Article>
        <S.Aside>
          {comments && (
            <CommentsPanel
              nodeId={n.id}
              canComment={!!page.space?.permissions.includes('comment')}
            />
          )}
          <PageToc headings={headingsOf(page.content)} />
          <PageMeta metadata={page.metadata} status={n.status} version={n.version} />
          <PageQuality
            node={n}
            canManage={owner === me.handle || !!page.space?.permissions.includes('admin')}
          />
        </S.Aside>
      </S.Layout>
    </S.Page>
  );
}
