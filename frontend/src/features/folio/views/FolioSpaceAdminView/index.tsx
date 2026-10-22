import { useParams } from '@tanstack/react-router';
import { SpacePage } from '../../components/SpacePage';

/** "Manage" (RAD-57): the space's admin mode. For now its pages, tree and settings. */
export function FolioSpaceAdminView() {
  const { key } = useParams({ strict: false }) as { key: string };
  return <SpacePage spaceKey={key} />;
}
