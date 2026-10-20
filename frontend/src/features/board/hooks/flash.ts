import { createContext, useContext } from 'react';

/** The card that just moved: a short flash, brighter when it reached a done column. */
export type Flash = { key: string; kind: 'moved' | 'done' };

export const FlashContext = createContext<Flash | null>(null);

export function useFlash(ticketKey: string): Flash['kind'] | undefined {
  const flash = useContext(FlashContext);
  return flash?.key === ticketKey ? flash.kind : undefined;
}
