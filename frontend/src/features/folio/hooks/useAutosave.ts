import { useCallback, useEffect, useRef, useState } from 'react';

export type SaveState = 'saved' | 'unsaved' | 'saving' | 'error';

/** Calls `save` once changes stop for `delay` ms; one save at a time, the latest wins. */
export function useAutosave<T>(save: (value: T) => Promise<unknown>, delay = 800) {
  const [state, setState] = useState<SaveState>('saved');
  const pending = useRef<{ value: T } | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const running = useRef(false);
  const saveRef = useRef(save);
  saveRef.current = save;

  const flush = useCallback(async () => {
    clearTimeout(timer.current);
    if (running.current || !pending.current) return;
    const { value } = pending.current;
    pending.current = null;
    running.current = true;
    setState('saving');
    try {
      await saveRef.current(value);
      setState(pending.current ? 'unsaved' : 'saved');
    } catch {
      pending.current ??= { value }; // try again with the next change or flush
      setState('error');
    } finally {
      running.current = false;
    }
    if (pending.current) timer.current = setTimeout(() => void flush(), delay);
  }, [delay]);

  const change = useCallback(
    (value: T) => {
      pending.current = { value };
      setState('unsaved');
      clearTimeout(timer.current);
      timer.current = setTimeout(() => void flush(), delay);
    },
    [delay, flush],
  );

  // Leaving the editor saves what is left; closing the tab with changes asks first.
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (pending.current || running.current) event.preventDefault();
    };
    window.addEventListener('beforeunload', warn);
    return () => {
      window.removeEventListener('beforeunload', warn);
      void flush();
    };
  }, [flush]);

  return { state, change, flush };
}
