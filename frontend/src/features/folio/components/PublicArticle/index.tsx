import { useTranslation } from 'react-i18next';
import { formatDate } from '../../../../lib/format';
import type { PublicPage } from '../../../../services/api/folioPublic';
import { DocContent } from '../DocContent';
import type { DocNode } from '../DocContent/anchors';
import { readingMinutes } from '../DocContent/anchors';
import { DocEnvContext, type DocEnv } from '../DocContent/env';
import { RootsArt } from '../RootsArt';
import * as S from './style';

type Props = {
  page: PublicPage;
  /** Where its files are read without an account, and how child pages link. */
  env: Omit<DocEnv, 'isPublic'>;
};

/** One page in the magazine view outside Folio (a public link, a PDF): cover, title, lead
 * and content, without comments, actions or anything that needs an account. */
export function PublicArticle({ page, env: links }: Props) {
  const { t } = useTranslation();
  const doc = page.content_json as DocNode;
  const description = page.metadata.description ? String(page.metadata.description) : '';
  const env: DocEnv = { ...links, isPublic: true };

  return (
    <div>
      <S.Cover $image={page.cover_asset_id ? env.assetUrl(page.cover_asset_id) : null} aria-hidden>
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
