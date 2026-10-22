import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { type FolioDoc, queryDocs } from '../../../../services/api/folio';
import {
  fetchSpaceOverview,
  spaceKeys,
  type SpaceSectionKey,
} from '../../../../services/api/folioSpaces';
import { SECTIONS, sectionQuery } from '../../sections';
import { RootsArt } from '../RootsArt';
import * as S from './style';

type Meta = { description?: string; owner?: string };
const meta = (doc: FolioDoc) => (doc.metadata ?? {}) as Meta;
const pagePath = (doc: FolioDoc) => `/folio/p/${doc.id}-${doc.slug}`;

function useDocs(key: readonly unknown[], rql: string, limit: number, enabled = true) {
  return useQuery({
    queryKey: ['folio', 'portada', ...key],
    queryFn: async () => (await queryDocs(rql, limit)).items,
    enabled,
  });
}

/** A space's portada (RAD-57): where to start, then the latest of each section in bento. */
export function SpacePortada({ space }: { space: string }) {
  const { t, i18n } = useTranslation();
  const overview = useQuery({
    queryKey: spaceKeys.overview(space),
    queryFn: () => fetchSpaceOverview(space),
  });
  const shown = (key: SpaceSectionKey) =>
    overview.data?.sections.some((s) => s.key === key && s.visible && s.count > 0) ?? false;
  const count = (key: SpaceSectionKey) =>
    overview.data?.sections.find((s) => s.key === key)?.count ?? 0;

  const pinned = useDocs([space, 'start'], `space = ${space} AND label = start-here`, 1);
  const guides = useDocs([space, 'guides'], sectionQuery(space, 'guides'), 4, shown('guides'));
  const specs = useDocs([space, 'specs'], sectionQuery(space, 'specs'), 2, shown('specs'));
  const decisions = useDocs(
    [space, 'decisions'],
    sectionQuery(space, 'decisions'),
    2,
    shown('decisions'),
  );
  const recent = useDocs([space, 'recent'], `space = ${space} ORDER BY updated DESC`, 4);
  const date = new Intl.DateTimeFormat(i18n.language, { day: 'numeric', month: 'short' });

  const start = pinned.data?.[0] ?? guides.data?.[0];
  const moreGuides = (guides.data ?? []).filter((g) => g.id !== start?.id).slice(0, 3);
  const sectionPath = (key: SpaceSectionKey) => `/folio/s/${space}/${SECTIONS[key].path}`;
  const seeAll = (key: SpaceSectionKey) => (
    <S.More to={sectionPath(key)}>{t('folio.portada.seeAll', { count: count(key) })}</S.More>
  );

  if (recent.data && recent.data.length === 0) return <S.Empty>{t('folio.portada.empty')}</S.Empty>;

  return (
    <S.Bento>
      {start && (
        <S.Start to={pagePath(start)}>
          <S.Cover>
            <RootsArt />
          </S.Cover>
          <S.StartBody>
            <S.Tag>{t('folio.portada.startHere')}</S.Tag>
            <h2>{start.title}</h2>
            {meta(start).description && <p>{meta(start).description}</p>}
          </S.StartBody>
        </S.Start>
      )}
      {specs.data && specs.data.length > 0 && (
        <S.Card $tone="lime" $wide>
          <S.Head>
            <S.Kicker>{t('folio.sections.specs.label')}</S.Kicker>
            {seeAll('specs')}
          </S.Head>
          {specs.data.map((doc) => (
            <S.Inner key={doc.id} to={pagePath(doc)}>
              <b>{doc.title}</b>
              {meta(doc).description && <span>{meta(doc).description}</span>}
            </S.Inner>
          ))}
        </S.Card>
      )}
      {decisions.data && decisions.data.length > 0 && (
        <S.Card>
          <S.Kicker>{t('folio.sections.decisions.label')}</S.Kicker>
          {decisions.data.map((doc) => (
            <S.Title key={doc.id} to={pagePath(doc)}>
              {doc.title}
            </S.Title>
          ))}
          {seeAll('decisions')}
        </S.Card>
      )}
      {moreGuides.length > 0 && (
        <S.Card $wide>
          <S.Head>
            <S.Kicker>{t('folio.sections.guides.label')}</S.Kicker>
            {seeAll('guides')}
          </S.Head>
          {moreGuides.map((doc) => (
            <S.Row key={doc.id} to={pagePath(doc)}>
              {doc.title}
              {doc.published_at && <small>{date.format(new Date(doc.published_at))}</small>}
            </S.Row>
          ))}
        </S.Card>
      )}
      {recent.data && recent.data.length > 0 && (
        <S.Card $wide>
          <S.Kicker>{t('folio.portada.recent')}</S.Kicker>
          {recent.data.map((doc) => (
            <S.Row key={doc.id} to={pagePath(doc)}>
              {doc.title}
              <small>{date.format(new Date(doc.updated_at))}</small>
            </S.Row>
          ))}
        </S.Card>
      )}
    </S.Bento>
  );
}
