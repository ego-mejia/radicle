import { useParams } from '@tanstack/react-router';
import { TicketDetail } from '../../components/TicketDetail';

export function TicketPageView() {
  const { key } = useParams({ from: '/app/t/$key' });
  return <TicketDetail key={key} ticketKey={key.toUpperCase()} />;
}
