import { useNavigate, useParams } from '@tanstack/react-router';
import { useEffect } from 'react';
import { TicketDetail } from '../../components/TicketDetail';
import { useTicket } from '../../hooks/useTicket';

export function TicketPageView() {
  const { key } = useParams({ from: '/app/t/$key' });
  const navigate = useNavigate();
  const { data: ticket } = useTicket(key.toUpperCase());
  // An old key of a moved ticket redirects to its new URL.
  useEffect(() => {
    if (ticket && ticket.key !== key.toUpperCase()) {
      void navigate({ to: '/t/$key', params: { key: ticket.key }, replace: true });
    }
  }, [ticket, key, navigate]);
  return <TicketDetail key={key} ticketKey={key.toUpperCase()} />;
}
