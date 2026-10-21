import { useParams } from '@tanstack/react-router';
import { SpacePage } from '../../components/SpacePage';

/** A space: its cover, the page tree and its blog posts. */
export function FolioSpaceView() {
  const { key } = useParams({ from: '/folio/folio/s/$key' });
  return <SpacePage spaceKey={key} />;
}
