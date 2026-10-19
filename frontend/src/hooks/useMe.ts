import { useQuery } from '@tanstack/react-query';
import { authKeys, fetchMe } from '../services/api/auth';
import type { Me } from '../services/api/types';

/** The signed-in user. Routes under the app shell guarantee it is loaded. */
export function useMe(): Me {
  const { data } = useQuery({ queryKey: authKeys.me, queryFn: fetchMe, staleTime: 60_000 });
  if (!data) throw new Error('useMe used outside the authenticated app');
  return data;
}
