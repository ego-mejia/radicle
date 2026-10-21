import { useQuery } from '@tanstack/react-query';
import { aiKeys, fetchAiAvailability } from '../../../services/api/folioAi';

/** Whether the editor shows its AI in this space (Folio 4.6). Off while loading or when the
 * request fails: without a provider nothing AI appears. */
export function useEditorAi(space: string): boolean {
  const query = useQuery({
    queryKey: aiKeys.availability(space),
    queryFn: () => fetchAiAvailability(space),
    staleTime: 5 * 60_000,
    retry: false,
  });
  return query.data?.available ?? false;
}
