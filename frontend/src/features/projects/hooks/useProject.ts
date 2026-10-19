import { useQuery } from '@tanstack/react-query';
import { fetchProject, projectKeys } from '../../../services/api/projects';

export function useProject(key: string) {
  return useQuery({ queryKey: projectKeys.detail(key), queryFn: () => fetchProject(key) });
}

/** Members who can be assigned (member or admin), for pickers and @mentions. */
export function assignable(
  members: { handle: string; display_name: string; role: string; kind: string }[],
) {
  return members.filter((m) => m.role !== 'viewer');
}
