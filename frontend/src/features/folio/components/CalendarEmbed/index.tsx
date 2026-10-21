import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { CalendarDays, Lock } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { isApiError } from '../../../../services/api/client';
import { calendarKeys, fetchCalendar } from '../../../../services/api/folioCalendars';
import type { CalendarMode } from '../../calendar/dates';
import { CalendarView } from '../CalendarView';
import * as S from './style';

/** A calendar inside a page or on the home (Folio 5.8), with a link to its space's
 * calendars. Whoever can't see it sees a placeholder instead. */
export function CalendarEmbed({ calendarId, view }: { calendarId: string; view?: CalendarMode }) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const [mode, setMode] = useState<CalendarMode>(view ?? 'month');
  const calendar = useQuery({
    queryKey: calendarKeys.calendar(calendarId),
    queryFn: () => fetchCalendar(calendarId),
    retry: false,
  });

  if (calendar.isError) {
    if (isApiError(calendar.error, 404))
      return (
        <S.NoAccess role="note">
          <Lock aria-hidden />
          {t('folio.calendar.block.noAccess')}
        </S.NoAccess>
      );
    return <S.Error role="alert">{errorMessage(calendar.error)}</S.Error>;
  }
  if (!calendar.data) return <PageSpinner />;
  return (
    <S.Embed>
      <S.Head>
        <CalendarDays aria-hidden />
        <Link to="/folio/s/$key/calendar" params={{ key: calendar.data.space }}>
          {t('folio.calendar.block.open')}
        </Link>
      </S.Head>
      <CalendarView calendar={calendar.data} mode={mode} onModeChange={setMode} />
    </S.Embed>
  );
}
