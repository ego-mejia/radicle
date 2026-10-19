/**
 * Single-key ticket shortcuts (e, a, m, l, p) reach the open ticket through a window
 * event, so the components that own each control react without prop drilling.
 */
export type TicketCommand = 'edit-title' | 'assign-me' | 'move' | 'tags' | 'priority';

const EVENT = 'radicle:ticket-command';

export function sendTicketCommand(command: TicketCommand): void {
  window.dispatchEvent(new CustomEvent<TicketCommand>(EVENT, { detail: command }));
}

export function onTicketCommand(handler: (command: TicketCommand) => void): () => void {
  const listener = (e: Event) => handler((e as CustomEvent<TicketCommand>).detail);
  window.addEventListener(EVENT, listener);
  return () => window.removeEventListener(EVENT, listener);
}

const RECENT_KEY = 'radicle.recent';

export type Recent = { key: string; title: string };

export function recentTickets(): Recent[] {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) ?? '[]') as Recent[];
  } catch {
    return [];
  }
}

export function rememberTicket(item: Recent): void {
  try {
    const next = [item, ...recentTickets().filter((r) => r.key !== item.key)].slice(0, 8);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  } catch {
    // Storage can be unavailable; recents are only a convenience.
  }
}
