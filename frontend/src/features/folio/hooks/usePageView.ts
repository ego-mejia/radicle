import { useEffect, useRef } from 'react';
import { recordView } from '../../../services/api/folioAnalytics';

/** Counts a read once per page opened (Folio 5.9). Analytics never get in the reader's way,
 * so a failure is ignored. */
export function usePageView(nodeId: string | undefined, enabled: boolean) {
  const counted = useRef<string | null>(null);
  useEffect(() => {
    if (!nodeId || !enabled || counted.current === nodeId) return;
    counted.current = nodeId;
    recordView(nodeId).catch(() => undefined);
  }, [nodeId, enabled]);
}
