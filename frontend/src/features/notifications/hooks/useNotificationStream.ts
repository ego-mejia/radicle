import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';
import { notificationKeys, STREAM_URL } from '../../../services/api/notifications';

const MAX_DELAY = 30_000;

/**
 * Listens to the server's notification stream and refreshes the bell when one arrives.
 * A dropped connection reconnects after 1 s, 2 s, 4 s… up to 30 s; without EventSource
 * (tests, old browsers) the list falls back to its polling interval.
 */
export function useNotificationStream() {
  const queryClient = useQueryClient();
  useEffect(() => {
    if (typeof EventSource === 'undefined') return;
    let source: EventSource | null = null;
    let delay = 1_000;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let closed = false;

    const connect = () => {
      source = new EventSource(STREAM_URL, { withCredentials: true });
      source.addEventListener('ready', () => {
        delay = 1_000;
      });
      source.addEventListener('notification', () => {
        void queryClient.invalidateQueries({ queryKey: notificationKeys.list });
      });
      source.onerror = () => {
        source?.close();
        if (closed) return;
        timer = setTimeout(connect, delay);
        delay = Math.min(delay * 2, MAX_DELAY);
      };
    };
    connect();
    return () => {
      closed = true;
      clearTimeout(timer);
      source?.close();
    };
  }, [queryClient]);
}
