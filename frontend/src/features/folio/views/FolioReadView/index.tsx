import { useParams } from '@tanstack/react-router';
import { nodeIdFrom } from '../../../../services/api/folio';
import { ReadPage } from '../../components/ReadPage';

/** Reading a page: magazine by default, focus mode on demand. */
export function FolioReadView() {
  const { page } = useParams({ from: '/folio/folio/p/$page' });
  return <ReadPage nodeId={nodeIdFrom(page)} />;
}
