import { useQuery } from '@tanstack/react-query';
import { useParams, useSearch } from '@tanstack/react-router';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { fetchNode, folioKeys, nodeIdFrom } from '../../../../services/api/folio';
import { LiveDocHistory } from '../../components/LiveDocHistory';
import { PageHistory } from '../../components/PageHistory';

/** /folio/p/$page/history?from&to: a page's versions and their diff, or a live doc's snapshots. */
export function FolioHistoryView() {
  const { page } = useParams({ from: '/folio/folio/p/$page/history' });
  const { from, to } = useSearch({ from: '/folio/folio/p/$page/history' });
  const nodeId = nodeIdFrom(page);
  const node = useQuery({ queryKey: folioKeys.node(nodeId), queryFn: () => fetchNode(nodeId) });
  if (node.isPending) return <PageSpinner />;
  if (node.data?.kind === 'live_doc') return <LiveDocHistory node={node.data} />;
  return <PageHistory nodeId={nodeId} from={from} to={to} />;
}
