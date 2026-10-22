import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { fetchNode, folioKeys } from '../../../services/api/folio';
import { fetchProject, fetchProjects, projectKeys } from '../../../services/api/projects';

export type TicketType = 'task' | 'bug' | 'draft';

/** Where new Docket tickets go: project, type, area and milestone, with the project's open
 * areas and milestones to choose from. Until you pick, the project is the doc's own Docket
 * project (its `docket_project` metadata) when you can see it, else the first one. */
export function useTicketTarget(nodeId?: string) {
  const [project, setProject] = useState('');
  const [type, setType] = useState<TicketType>('task');
  const [area, setArea] = useState('');
  const [milestone, setMilestone] = useState('');
  const projects = useQuery({ queryKey: projectKeys.list(false), queryFn: () => fetchProjects() });
  const node = useQuery({
    queryKey: folioKeys.node(nodeId ?? ''),
    queryFn: () => fetchNode(nodeId ?? ''),
    enabled: !!nodeId,
  });
  const own = String(node.data?.metadata?.docket_project ?? '').toUpperCase();
  const fallback = projects.data?.find((p) => p.key === own)?.key ?? projects.data?.[0]?.key;
  const chosen = project || fallback || '';
  const detail = useQuery({
    queryKey: projectKeys.detail(chosen),
    queryFn: () => fetchProject(chosen),
    enabled: !!chosen,
  });
  return {
    project: chosen,
    type,
    area,
    milestone,
    projects: projects.data ?? [],
    areas: (detail.data?.areas ?? []).filter((a) => !a.archived),
    milestones: (detail.data?.milestones ?? []).filter((m) => m.status === 'open'),
    setProject: (key: string) => {
      setProject(key);
      setArea('');
      setMilestone('');
    },
    setType,
    setArea,
    setMilestone,
  };
}

export type TicketTarget = ReturnType<typeof useTicketTarget>;
