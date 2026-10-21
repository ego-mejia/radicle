import { Link } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { formatDate } from '../../../../../../lib/format';
import { publicAssetUrl, type PublicView } from '../../../../../../services/api/folioPublic';
import { DocContent } from '../../../../components/DocContent';
import type { DocNode } from '../../../../components/DocContent/anchors';
import { readingMinutes } from '../../../../components/DocContent/anchors';
import { DocEnvContext, type DocEnv } from '../../../../components/DocContent/env';
import { RootsArt } from '../../../../components/RootsArt';
import * as S from './style';

type Props = { token: string; page: NonNullable<PublicView['page']> };

/** One shared page in the magazine view: cover, title, lead and content, without people,
 * comments or anything that needs an account. */
export function PublicArticle({ token, page }: Props) {
  const { t } = useTranslation();
  const doc = page.content_json as DocNode;
  const description = page.metadata.description ? String(page.metadata.description) : '';
  const env: DocEnv = {
    assetUrl: (id) => publicAssetUrl(token, id),
    isPublic: true,
    pageLink: (c) => (
      <Link to="/pub/$token/$page" params={{ token, page: `${c.id}-${c.slug}` }}>
        {c.title}
      </Link>
    ),
  };

  return (
    <div>
      <S.Cover
        $image={page.cover_asset_id ? publicAssetUrl(token, page.cover_asset_id) : null}
        aria-hidden
      >
        {!page.cover_asset_id && <RootsArt />}
      </S.Cover>
      <S.Layout>
        <S.Article>
          {page.metadata.doc_type ? <S.Tag>{String(page.metadata.doc_type)}</S.Tag> : null}
          <S.Title>
            {page.icon && <span aria-hidden>{page.icon} </span>}
            {page.title}
          </S.Title>
          {description && <S.Lead>{description}</S.Lead>}
          <S.Byline>
            <span>
              {page.published_at && <>{formatDate(page.published_at.slice(0, 10))} · </>}
              {t('folio.reader.minutes', { count: readingMinutes(doc) })}
            </span>
          </S.Byline>
          <DocEnvContext.Provider value={env}>
            <DocContent doc={doc} childPages={page.children} size="large" />
          </DocEnvContext.Provider>
        </S.Article>
      </S.Layout>
    </div>
  );
}
