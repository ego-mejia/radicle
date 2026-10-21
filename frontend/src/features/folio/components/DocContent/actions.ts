import { createContext } from 'react';

/** What the page around a document lets its blocks do. Read-only places (previews,
 * embeds) leave it empty. */
export type DocActionsValue = {
  /** Create a Docket ticket from an action item (Folio 4.2). */
  onTicket?: (text: string, from: HTMLElement) => void;
};

export const DocActions = createContext<DocActionsValue>({});
