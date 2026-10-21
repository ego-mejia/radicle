import { createLink } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../../../components/ui/Badge';
import type { FolioHit } from '../../../../../../services/api/folio';
import { recordSearchClick } from '../../../../../../services/api/folioAnalytics';
import { Snippet } from '../../../../components/Snippet';
import { hitTarget } from '../../../../components/Snippet/hitTarget';
import { StatusBadge } from '../../../../components/StatusBadge';
import * as S from './style';

const TitleLink = createLink(S.Title);

/** One search result: where it is, its best section, the matching words and why it matched.
 * Opening it tells analytics which result the search led to. */
export function SearchHit({ hit, searchId }: { hit: FolioHit; searchId?: string | null }) {
  const { t } = useTranslation();
  const { page, hash } = hitTarget(hit.url);
  return (
    <S.Item>
      <S.Path>{[hit.space, ...hit.section].join(' › ')}</S.Path>
      <TitleLink
        to="/folio/p/$page"
        params={{ page }}
        hash={hash}
        onClick={() => {
          if (searchId) recordSearchClick(searchId, hit.node_id).catch(() => undefined);
        }}
      >
        {hit.title}
      </TitleLink>
      <S.Snippet>
        <Snippet text={hit.snippet || hit.description} />
      </S.Snippet>
      <S.Tags>
        <StatusBadge status={hit.status} />
        {hit.doc_type && <Badge mono>{hit.doc_type}</Badge>}
        {hit.matched_by.map((m) => (
          <Badge key={m} tone="accent">
            {t(`folio.searchPage.matchedBy.${m}`)}
          </Badge>
        ))}
      </S.Tags>
    </S.Item>
  );
}
