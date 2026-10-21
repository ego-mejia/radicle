import { useQuery } from '@tanstack/react-query';
import { useNavigate, useSearch } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { FormError } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { Spinner } from '../../../../components/ui/Spinner';
import { Tabs } from '../../../../components/ui/Tabs';
import {
  folioKeys,
  searchDocs,
  type SearchFilters as Filters,
  type SearchMode,
} from '../../../../services/api/folio';
import { RqlBar } from './components/RqlBar';
import { SearchFilters } from './components/SearchFilters';
import { SearchHit } from './components/SearchHit';
import * as S from './style';

const MODES: SearchMode[] = ['hybrid', 'text', 'semantic'];

/** Hybrid search with filters (Folio 1.8). The words and the mode live in the URL. */
export function FolioSearchView() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const params = useSearch({ strict: false }) as { q?: string; mode?: SearchMode; rql?: string };
  const q = params.q ?? '';
  const mode = params.mode ?? 'hybrid';
  const [draft, setDraft] = useState(q);
  const [filters, setFilters] = useState<Filters>({});
  const go = (next: { q?: string; mode?: SearchMode; rql?: string }) =>
    void navigate({ to: '/folio/search', search: { q, mode, rql: params.rql, ...next } });

  const results = useQuery({
    queryKey: folioKeys.search(q, mode, filters),
    queryFn: () => searchDocs(q, mode, filters, 20),
    enabled: q.trim().length > 0,
  });

  return (
    <S.Wrap>
      <PageTitle title={t('folio.searchPage.title')} />
      <S.Form
        role="search"
        onSubmit={(event) => {
          event.preventDefault();
          go({ q: draft.trim() });
        }}
      >
        <Input
          type="search"
          aria-label={t('folio.search')}
          placeholder={t('folio.searchPage.placeholder')}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <Button type="submit" variant="primary">
          {t('folio.searchPage.submit')}
        </Button>
      </S.Form>
      <Tabs
        label={t('folio.searchPage.mode')}
        value={mode}
        onChange={(next) => go({ mode: next })}
        tabs={MODES.map((id) => ({ id, label: t(`folio.searchPage.modes.${id}`) }))}
      />
      <SearchFilters value={filters} onChange={setFilters} />
      {!q && <S.Note>{t('folio.searchPage.hint')}</S.Note>}
      {results.isFetching && <Spinner />}
      <FormError>{results.error?.message}</FormError>
      {results.data &&
        (results.data.items.length === 0 ? (
          <S.Note>{t('folio.searchPage.none', { q })}</S.Note>
        ) : (
          <S.Results aria-label={t('folio.searchPage.results')}>
            {results.data.items.map((hit) => (
              <SearchHit key={hit.node_id} hit={hit} searchId={results.data.search_id} />
            ))}
          </S.Results>
        ))}
      <RqlBar rql={params.rql ?? ''} onRun={(rql) => go({ rql: rql || undefined })} />
    </S.Wrap>
  );
}
