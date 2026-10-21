import { useQuery } from '@tanstack/react-query';
import type { SuiteApp } from '../lib/suite';
import { fetchFolioMe, folioKeys } from '../services/api/folio';

/** The apps the signed-in user can open: Docket always, Folio when a grant reaches them. */
export function useSuiteApps(): SuiteApp[] {
  const { data: folio } = useQuery({
    queryKey: folioKeys.me,
    queryFn: fetchFolioMe,
    staleTime: 60_000,
  });
  return folio ? ['docket', 'folio'] : ['docket'];
}
