import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { CalendarDays, FilePlus, FolderPlus, PenLine, Radio, Shapes, Table2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import {
  assetUrl,
  fetchPosts,
  fetchSpace,
  fetchTree,
  folioKeys,
} from '../../../../services/api/folio';
import { type NewKind, NewNodeDialog } from '../NewNodeDialog';
import { SpaceTree } from '../SpaceTree';
import { StatusBadge } from '../StatusBadge';
import { ArchivedList } from '../ArchivedList';
import { MyShortcuts } from '../MyShortcuts';
import { ExportMenu } from '../ExportMenu';
import { SpaceSettings } from '../SpaceSettings';
import * as S from './style';

/** A space: its cover and description, the page tree and its blog posts. */
export function SpacePage({ spaceKey }: { spaceKey: string }) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const [creating, setCreating] = useState<NewKind | null>(null);
  const space = useQuery({
    queryKey: folioKeys.space(spaceKey),
    queryFn: () => fetchSpace(spaceKey),
  });
  const tree = useQuery({ queryKey: folioKeys.tree(spaceKey), queryFn: () => fetchTree(spaceKey) });
  const posts = useQuery({
    queryKey: folioKeys.posts(spaceKey),
    queryFn: () => fetchPosts(spaceKey),
  });

  if (space.isPending) return <PageSpinner />;
  if (space.isError)
    return <EmptyState title={t('folio.space.notFound')} text={errorMessage(space.error)} />;
  const s = space.data;
  const canCreate = s.permissions.includes('create');

  return (
    <S.Page>
      <S.Cover $image={s.cover_asset_id ? assetUrl(s.cover_asset_id) : null}>
        <S.CoverInner>
          <S.Mark aria-hidden>{s.icon || s.name.slice(0, 1).toUpperCase()}</S.Mark>
          <S.Heading>
            {s.kind === 'personal' && <S.Kind>{t('folio.space.personal')}</S.Kind>}
            <h1>{s.name}</h1>
            {s.description && <p>{s.description}</p>}
          </S.Heading>
          {s.permissions.includes('admin') && <SpaceSettings space={s} />}
          {s.permissions.includes('export') && <ExportMenu target={{ space: s.key }} />}
          {canCreate && (
            <S.Actions>
              <Button variant="primary" onClick={() => setCreating('page')}>
                <FilePlus aria-hidden />
                {t('folio.space.new.page')}
              </Button>
              <Button onClick={() => setCreating('blog_post')}>
                <PenLine aria-hidden />
                {t('folio.space.new.blog_post')}
              </Button>
              <Button onClick={() => setCreating('live_doc')}>
                <Radio aria-hidden />
                {t('folio.space.new.live_doc')}
              </Button>
              <Button onClick={() => setCreating('folder')}>
                <FolderPlus aria-hidden />
                {t('folio.space.new.folder')}
              </Button>
              <Button onClick={() => setCreating('database')}>
                <Table2 aria-hidden />
                {t('folio.space.new.database')}
              </Button>
              <Button onClick={() => setCreating('whiteboard')}>
                <Shapes aria-hidden />
                {t('folio.space.new.whiteboard')}
              </Button>
            </S.Actions>
          )}
        </S.CoverInner>
      </S.Cover>

      <S.Body>
        <S.Side>
          <MyShortcuts />
          <S.SideLink>
            <Link to="/folio/s/$key/calendar" params={{ key: spaceKey }}>
              <CalendarDays aria-hidden />
              {t('folio.calendar.title')}
            </Link>
          </S.SideLink>
          <S.SideTitle>{t('folio.space.pages')}</S.SideTitle>
          {tree.data ? (
            <SpaceTree space={spaceKey} items={tree.data} canMove={canCreate} />
          ) : (
            <PageSpinner />
          )}
          <ArchivedList space={spaceKey} canRestore={canCreate} />
        </S.Side>
        <S.Main>
          <S.SectionTitle>{t('folio.space.posts')}</S.SectionTitle>
          {posts.data && posts.data.length === 0 && <S.Muted>{t('folio.space.noPosts')}</S.Muted>}
          <S.Posts>
            {posts.data?.map((post) => (
              <li key={post.id}>
                <Link to="/folio/p/$page" params={{ page: `${post.id}-${post.slug}` }}>
                  {post.icon && <span aria-hidden>{post.icon}</span>}
                  {post.title}
                  <StatusBadge status={post.status} />
                </Link>
              </li>
            ))}
          </S.Posts>
        </S.Main>
      </S.Body>

      {creating && (
        <NewNodeDialog
          space={spaceKey}
          kind={creating}
          open
          onOpenChange={(open) => !open && setCreating(null)}
        />
      )}
    </S.Page>
  );
}
