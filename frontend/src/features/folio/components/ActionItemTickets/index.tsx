import { type ReactNode, type RefObject, useMemo, useState } from 'react';
import { DocActions } from '../DocContent/actions';
import { sectionAt } from '../../hooks/textAnchor';
import { CreateTicketDialog } from '../CreateTicketDialog';

type Props = {
  nodeId: string;
  /** The page's content, to find the section an action item is in. */
  container: RefObject<HTMLElement | null>;
  children: ReactNode;
};

/** Lets the action items of a page become Docket tickets (Folio 4.2), linked to the
 * section they are in. */
export function ActionItemTickets({ nodeId, container, children }: Props) {
  const [item, setItem] = useState<{ text: string; anchor: string | null } | null>(null);
  const value = useMemo(
    () => ({
      onTicket: (text: string, from: HTMLElement) => {
        const root = container.current;
        setItem({ text, anchor: root ? sectionAt(root, from) : null });
      },
    }),
    [container],
  );
  return (
    <DocActions.Provider value={value}>
      {children}
      {item ? (
        <CreateTicketDialog
          nodeId={nodeId}
          text={item.text}
          anchor={item.anchor}
          onClose={() => setItem(null)}
        />
      ) : null}
    </DocActions.Provider>
  );
}
