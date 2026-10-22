import { useQuery } from '@tanstack/react-query';
import { useParams } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { fetchSpace, folioKeys } from '../../../../services/api/folio';
import type { DecisionFilters, SpecFilters } from '../../../../services/api/folioSections';
import type { SpaceSectionKey } from '../../../../services/api/folioSpaces';
import { DecisionsTable } from '../../components/DecisionsTable';
import { NewNodeDialog } from '../../components/NewNodeDialog';
import { GuidesSection } from '../../components/GuidesSection';
import { SectionDocs } from '../../components/SectionDocs';
import { SpaceHero } from '../../components/SpaceHero';
import { SpecsTable } from '../../components/SpecsTable';
import * as S from './style';

/** One section of a space (RAD-57): its hero and its pages. Specs and architecture
 * decisions have their own tables; the hero's search is the table's text filter. */
export function FolioSectionView({ section }: { section: SpaceSectionKey }) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const { key } = useParams({ strict: false }) as { key: string };
  const [q, setQ] = useState('');
  const [writing, setWriting] = useState(false);
  const [specs, setSpecs] = useState<SpecFilters>({ features: [] });
  const [decisions, setDecisions] = useState<DecisionFilters>({ status: 'current' });
  const space = useQuery({ queryKey: folioKeys.space(key), queryFn: () => fetchSpace(key) });
  if (space.isPending) return <PageSpinner />;
  if (space.isError)
    return <EmptyState title={t('folio.space.notFound')} text={errorMessage(space.error)} />;
  const canCreate = space.data.permissions.includes('create');
  return (
    <>
      <SpaceHero
        space={space.data}
        active={section}
        onSearch={setQ}
        query={q}
        onWrite={canCreate ? () => setWriting(true) : undefined}
      />
      <S.Body>
        {section === 'specs' ? (
          <SpecsTable
            space={key}
            filters={{ ...specs, q: q || undefined }}
            onFiltersChange={(f) => {
              setSpecs(f);
              setQ(f.q ?? '');
            }}
          />
        ) : section === 'decisions' ? (
          <DecisionsTable
            space={key}
            filters={{ ...decisions, q: q || undefined }}
            onFiltersChange={(f) => {
              setDecisions(f);
              setQ(f.q ?? '');
            }}
          />
        ) : section === 'guides' && !q ? (
          <GuidesSection space={key} />
        ) : (
          <SectionDocs space={key} section={section} q={q} />
        )}
      </S.Body>
      {writing && (
        <NewNodeDialog space={key} kind="page" open onOpenChange={(open) => setWriting(open)} />
      )}
    </>
  );
}
