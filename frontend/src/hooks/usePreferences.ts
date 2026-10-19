import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchPreferences, patchPreferences, workKeys } from '../services/api/work';
import type { Preferences } from '../services/api/types';
import { useMe } from './useMe';

/** Server-side preferences of the signed-in person (people only; agents have none). */
export function usePreferences() {
  const me = useMe();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: workKeys.preferences,
    queryFn: fetchPreferences,
    enabled: me.kind === 'human',
    staleTime: Infinity,
  });
  const save = useMutation({
    mutationFn: (changes: Partial<Preferences>) => patchPreferences(changes),
    onSuccess: (prefs) => queryClient.setQueryData(workKeys.preferences, prefs),
  });
  return { prefs: query.data, save: save.mutate };
}
