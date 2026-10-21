import { Link } from '@tanstack/react-router';
import { History, PenLine } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Avatar } from '../../../../components/ui/Avatar';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { formatDate } from '../../../../lib/format';
import { assetUrl } from '../../../../services/api/folio';
import { DocContent } from '../DocContent';
import { headingsOf, readingMinutes } from '../DocContent/anchors';
import { PageMeta } from '../PageMeta';
import { PageToc } from '../PageToc';
import * as S from './style';
import { usePage } from '../../hooks/usePage';

/** Reading a page in the magazine view: cover, title, lead, byline, content and index. */
export function ReadPage({ nodeId }: { nodeId: string }) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const page = usePage(nodeId);
  const { node } = page;

  if (node.isPending) return <PageSpinner />;
  if (node.isError)
    return <EmptyState title={t('folio.reader.unavailable')} text={errorMessage(node.error)} />;
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
        {page.canEdit && (
          <S.Actions>
            {n.version != null && (
              <Link to="/folio/p/$page/history" params={params}>
                <History aria-hidden />
                {t('folio.reader.history')}
              </Link>
            )}
            <Link to="/folio/p/$page/edit" params={params}>
              <PenLine aria-hidden />
              {t('folio.reader.edit')}
            </Link>
          </S.Actions>
        )}
      </S.Bar>

      <S.Cover $image={n.cover_asset_id ? assetUrl(n.cover_asset_id) : null} aria-hidden />

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
          <DocContent doc={page.content} childPages={page.children} size="large" />
        </S.Article>
        <S.Aside>
          <PageToc headings={headingsOf(page.content)} />
          <PageMeta metadata={page.metadata} status={n.status} version={n.version} />
        </S.Aside>
      </S.Layout>
    </S.Page>
  );
}
