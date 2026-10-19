import { useNavigate } from '@tanstack/react-router';
import { useContext, useEffect, useRef, useState } from 'react';
import { ShortcutsContext } from '../../../../contexts/shortcuts';
import { CommandPalette } from '../../../../features/palette/components/CommandPalette';
import { typingIn } from '../../../../hooks/useHotkey';
import { type TicketCommand, sendTicketCommand } from '../../../../lib/ticketCommands';
import { ShortcutHelp } from '../ShortcutHelp';

const TICKET_KEYS: Record<string, TicketCommand> = {
  e: 'edit-title',
  a: 'assign-me',
  m: 'move',
  l: 'tags',
  p: 'priority',
};

/** Moves focus between `[data-nav-item]` elements of the page (rows and cards). */
function moveFocus(delta: number) {
  const items = Array.from(
    document.querySelectorAll<HTMLElement>('#content [data-nav-item]'),
  ).filter((el) => el.offsetParent !== null);
  if (!items.length) return;
  const current = items.indexOf(document.activeElement as HTMLElement);
  const next = items[Math.min(items.length - 1, Math.max(0, current + delta))] ?? items[0]!;
  next.focus();
  next.scrollIntoView({ block: 'nearest' });
}

/**
 * Keyboard layer for the whole app: ⌘K palette (always), and when shortcuts are on,
 * `?` help, `g p` / `g m` navigation, `j` / `k` focus and the ticket keys.
 */
export function GlobalShortcuts() {
  const navigate = useNavigate();
  const enabled = useContext(ShortcutsContext);
  const [palette, setPalette] = useState(false);
  const [help, setHelp] = useState(false);
  const pendingG = useRef(0);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPalette((open) => !open);
        return;
      }
      if (!enabled || event.metaKey || event.ctrlKey || event.altKey || typingIn(event.target))
        return;
      if (document.querySelector('[role="dialog"]')) return;
      const key = event.key;
      if (Date.now() - pendingG.current < 1200) {
        pendingG.current = 0;
        if (key === 'p') void navigate({ to: '/' });
        if (key === 'm') void navigate({ to: '/me/tickets', search: {} });
        return;
      }
      if (key === 'g') {
        pendingG.current = Date.now();
        return;
      }
      if (key === '?') {
        event.preventDefault();
        setHelp(true);
      } else if (key === 'j' || key === 'k') {
        event.preventDefault();
        moveFocus(key === 'j' ? 1 : -1);
      } else if (TICKET_KEYS[key] && document.querySelector('[data-ticket-detail]')) {
        event.preventDefault();
        sendTicketCommand(TICKET_KEYS[key]!);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [enabled, navigate]);

  return (
    <>
      {palette && <CommandPalette onClose={() => setPalette(false)} />}
      {help && <ShortcutHelp onClose={() => setHelp(false)} />}
    </>
  );
}
