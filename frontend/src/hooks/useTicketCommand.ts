import { useEffect, useRef } from 'react';
import { type TicketCommand, onTicketCommand } from '../lib/ticketCommands';

/** Run `handler` when the open ticket receives `command` (see GlobalShortcuts). */
export function useTicketCommand(command: TicketCommand, handler: () => void, enabled = true) {
  const latest = useRef(handler);
  latest.current = handler;
  useEffect(() => {
    if (!enabled) return;
    return onTicketCommand((c) => c === command && latest.current());
  }, [command, enabled]);
}
