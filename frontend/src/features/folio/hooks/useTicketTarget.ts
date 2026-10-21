import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { fetchProject, fetchProjects, projectKeys } from '../../../services/api/projects';

export type TicketType = 'task' | 'bug' | 'draft';

/** Where new Docket tickets go: project (the first one until you pick), type, area and
 * milestone, with the project's open areas and milestones to choose from. */
export function useTicketTarget() {
  const [project, setProject] = useState('');
  const [type, setType] = useState<TicketType>('task');
  const [area, setArea] = useState('');
  const [milestone, setMilestone] = useState('');
  const projects = useQuery({ queryKey: projectKeys.list(false), queryFn: () => fetchProjects() });
  const chosen = project || projects.data?.[0]?.key || '';
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
