import { useParams } from '@tanstack/react-router';
import { CalendarsPage } from '../../components/CalendarsPage';

/** A space's calendars. */
export function FolioCalendarView() {
  const { key } = useParams({ from: '/folio/folio/s/$key/calendar' });
  return <CalendarsPage spaceKey={key} />;
}
