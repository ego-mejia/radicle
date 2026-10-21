import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';
import { TicketChip } from '../TicketChip';

/** A ticket smart link inside the editor: the same live chip the reader sees. */
export function TicketNodeView({ node }: NodeViewProps) {
  return (
    <NodeViewWrapper as="span" data-folio="ticket">
      <TicketChip ticketKey={String(node.attrs.key)} />
    </NodeViewWrapper>
  );
}
