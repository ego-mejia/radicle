import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { fetchProject, projectKeys } from '../../../services/api/projects';
import type { Area } from '../../../services/api/types';

/** Each area's color and icon by name, from the project (most pages have it cached). */
export function useAreaLook(projectKey: string | null | undefined): Map<string, Area> {
  const { data } = useQuery({
    queryKey: projectKeys.detail(projectKey ?? ''),
    queryFn: () => fetchProject(projectKey!),
    enabled: Boolean(projectKey),
  });
  return useMemo(() => new Map((data?.areas ?? []).map((a) => [a.name, a])), [data]);
}
