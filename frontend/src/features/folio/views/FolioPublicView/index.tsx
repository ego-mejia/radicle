import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from '@tanstack/react-router';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { nodeIdFrom } from '../../../../services/api/folio';
import { fetchPublic, publicAssetUrl, publicKeys } from '../../../../services/api/folioPublic';
import { PublicArticle } from '../../components/PublicArticle';
import * as S from './style';

/** A page or a space shared by a public link: read-only, without an account or the app's
 * bars. A space link adds its open pages on the side. */
export function FolioPublicView() {
  const { t } = useTranslation();
  const params = useParams({ strict: false }) as { token: string; page?: string };
  const token = params.token;
  const page = params.page ? nodeIdFrom(params.page) : null;
  const view = useQuery({
    queryKey: publicKeys.view(token, page),
    queryFn: () => fetchPublic(token, page),
    retry: false,
  });
  const title = view.data?.page?.title ?? view.data?.space.name;
  useEffect(() => {
    if (title) document.title = title;
  }, [title]);

  if (view.isPending) return <PageSpinner />;
  if (view.isError)
    return (
      <S.Page>
        <EmptyState title={t('folio.public.notFound')} text={t('folio.public.notFoundText')} />
      </S.Page>
    );

  const { space, nodes } = view.data;
  const isSpace = view.data.target_type === 'space';
  const pages = nodes.filter((n) => n.kind !== 'folder');
  const depth = (id: string | null, d = 0): number => {
    const parent = nodes.find((n) => n.id === id);
    return parent ? depth(parent.parent_id, d + 1) : d;
  };

  return (
    <S.Page>
      <S.Bar>
        <S.Space>
          {space.icon && <span aria-hidden>{space.icon} </span>}
          {isSpace ? (
            <Link to="/pub/$token" params={{ token }}>
              {space.name}
            </Link>
          ) : (
            space.name
          )}
        </S.Space>
        <S.Badge>{t('folio.public.badge')}</S.Badge>
      </S.Bar>
      <S.Body $withNav={isSpace}>
        {isSpace && (
          <S.Nav aria-label={t('folio.public.pages')}>
            {nodes.map((n) =>
              n.kind === 'folder' ? (
                <S.Folder key={n.id} $depth={depth(n.parent_id)}>
                  {n.title}
                </S.Folder>
              ) : (
                <S.NavItem key={n.id} $depth={depth(n.parent_id)}>
                  <Link
                    to="/pub/$token/$page"
                    params={{ token, page: `${n.id}-${n.slug}` }}
                    aria-current={n.id === page ? 'page' : undefined}
                  >
                    {n.icon && <span aria-hidden>{n.icon} </span>}
                    {n.title}
                  </Link>
                </S.NavItem>
              ),
            )}
          </S.Nav>
        )}
        {view.data.page ? (
          <PublicArticle
            page={view.data.page}
            env={{
              assetUrl: (id) => publicAssetUrl(token, id),
              pageLink: (c) => (
                <Link to="/pub/$token/$page" params={{ token, page: `${c.id}-${c.slug}` }}>
                  {c.title}
                </Link>
              ),
            }}
          />
        ) : (
          <S.Index>
            <h1>{space.name}</h1>
            {space.description && <p>{space.description}</p>}
            {!pages.length && <p>{t('folio.public.empty')}</p>}
          </S.Index>
        )}
      </S.Body>
    </S.Page>
  );
}
