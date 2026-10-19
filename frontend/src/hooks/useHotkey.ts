import { useContext, useEffect } from 'react';
import { ShortcutsContext } from '../contexts/shortcuts';

export function typingIn(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.isContentEditable ||
    ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) ||
    target.closest('.cm-editor') !== null
  );
}

/** Single-key shortcut that is ignored while the user types in a field. */
export function useHotkey(key: string, handler: () => void, enabled = true) {
  const shortcutsOn = useContext(ShortcutsContext);
  useEffect(() => {
    if (!enabled || !shortcutsOn) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey || typingIn(event.target)) return;
      if (event.key === key) {
        event.preventDefault();
        handler();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [key, handler, enabled, shortcutsOn]);
}
