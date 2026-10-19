import { useContext } from 'react';
import { CreateTicketContext } from '../contexts/createTicket';

/** Opens the global "Create ticket" modal, optionally prefilled. */
export function useCreateTicket() {
  return useContext(CreateTicketContext);
}
