import { useState } from 'react';

const key = (handle: string) => `radicle.folio.focus.${handle}`;

function read(handle: string): boolean {
  try {
    return localStorage.getItem(key(handle)) === '1';
  } catch {
    return false; // storage blocked: magazine view
  }
}

/** Whether this reader prefers focus mode; the choice is remembered per user. */
export function useFocusMode(handle: string): [boolean, (on: boolean) => void] {
  const [focus, setFocus] = useState(() => read(handle));
  const set = (on: boolean) => {
    setFocus(on);
    try {
      if (on) localStorage.setItem(key(handle), '1');
      else localStorage.removeItem(key(handle));
    } catch {
      // Storage blocked: the choice lasts until the page closes.
    }
  };
  return [focus, set];
}
