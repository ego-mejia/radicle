import { useParams, useSearch } from '@tanstack/react-router';
import { nodeIdFrom } from '../../../../services/api/folio';
import { PageHistory } from '../../components/PageHistory';

/** /folio/p/$page/history?from&to: a page's versions and their diff. */
export function FolioHistoryView() {
  const { page } = useParams({ from: '/folio/folio/p/$page/history' });
  const { from, to } = useSearch({ from: '/folio/folio/p/$page/history' });
  return <PageHistory nodeId={nodeIdFrom(page)} from={from} to={to} />;
}
