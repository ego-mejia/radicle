import { useQuery } from '@tanstack/react-query';
import { Check } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { Spinner } from '../../../../components/ui/Spinner';
import { type FolioDoc, queryDocs } from '../../../../services/api/folio';
import { fetchRecents, socialKeys } from '../../../../services/api/folioSocial';
import { sectionQuery } from '../../sections';
import * as S from './style';

const PATH_LABEL = 'getting-started';
const HIDDEN = new Set([PATH_LABEL, 'start-here']);
type Meta = { description?: string; labels?: string[] };
const meta = (doc: FolioDoc) => (doc.metadata ?? {}) as Meta;
const labelsOf = (doc: FolioDoc) =>
  (meta(doc).labels ?? []).map((l) => l.replace(/^#/, '')).filter((l) => !HIDDEN.has(l));
const href = (doc: FolioDoc) => `/folio/p/${doc.id}-${doc.slug}`;

/** The Guides section (RAD-57): the getting-started path, marking what you already read,
 * then every guide by category. */
export function GuidesSection({ space }: { space: string }) {
  const { t } = useTranslation();
  const [category, setCategory] = useState<string | null>(null);
  const path = useQuery({
    queryKey: ['folio', 'guides', space, 'path'],
    queryFn: async () =>
      (await queryDocs(sectionQuery(space, 'guides', `label = ${PATH_LABEL}`, 'title ASC'), 12))
        .items,
  });
  const all = useQuery({
    queryKey: ['folio', 'guides', space, 'all'],
    queryFn: async () => (await queryDocs(sectionQuery(space, 'guides'), 100)).items,
  });
  const recents = useQuery({ queryKey: socialKeys.recents, queryFn: fetchRecents });
  const read = new Set((recents.data ?? []).map((r) => r.id));

  if (all.isPending) return <Spinner />;
  if (all.isError)
    return <EmptyState title={t('folio.sectionDocs.error')} text={all.error.message} />;
  if (!all.data.length)
    return (
      <EmptyState title={t('folio.sectionDocs.empty')} text={t('folio.sectionDocs.emptyHint')} />
    );

  const steps = path.data ?? [];
  const next = steps.find((g) => !read.has(g.id));
  const categories = [...new Set(all.data.flatMap(labelsOf))].sort();
  const shown = category ? all.data.filter((g) => labelsOf(g).includes(category)) : all.data;

  return (
    <S.Wrap>
      {steps.length > 0 && (
        <section aria-labelledby="guides-path">
          <S.Heading id="guides-path">{t('folio.guides.path')}</S.Heading>
          <S.Steps>
            {steps.map((g, i) => {
              const done = read.has(g.id);
              const isNext = next?.id === g.id;
              return (
                <li key={g.id}>
                  <S.Step to={href(g)} $next={isNext}>
                    <S.Number $done={done} $next={isNext} aria-hidden>
                      {done ? <Check /> : i + 1}
                    </S.Number>
                    <b>{g.title}</b>
                    <small>
                      {done
                        ? t('folio.guides.read')
                        : isNext
                          ? t('folio.guides.next')
                          : t('folio.guides.pending')}
                    </small>
                  </S.Step>
                </li>
              );
            })}
          </S.Steps>
        </section>
      )}
      <section aria-labelledby="guides-all">
        <S.Bar>
          <S.Heading id="guides-all">{t('folio.guides.all')}</S.Heading>
          {categories.length > 0 && (
            <S.Chips role="group" aria-label={t('folio.guides.categories')}>
              <S.Chip type="button" aria-pressed={!category} onClick={() => setCategory(null)}>
                {t('folio.spaceHome.all')}
              </S.Chip>
              {categories.map((c) => (
                <S.Chip
                  key={c}
                  type="button"
                  aria-pressed={category === c}
                  onClick={() => setCategory(c)}
                >
                  {c}
                </S.Chip>
              ))}
            </S.Chips>
          )}
        </S.Bar>
        <S.Grid>
          {shown.map((g) => (
            <li key={g.id}>
              <S.Card to={href(g)}>
                {labelsOf(g)[0] && <S.Label>{labelsOf(g)[0]}</S.Label>}
                <b>{g.title}</b>
                {meta(g).description && <span>{meta(g).description}</span>}
              </S.Card>
            </li>
          ))}
        </S.Grid>
      </section>
    </S.Wrap>
  );
}
