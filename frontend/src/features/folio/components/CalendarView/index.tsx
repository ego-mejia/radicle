import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, Flag } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import {
  type CalendarEvent,
  type CalendarMilestone,
  calendarKeys,
  type EventCategory,
  fetchAgenda,
  type FolioCalendar,
} from '../../../../services/api/folioCalendars';
import { byDay, type CalendarMode, dayKey, shift, viewDays, viewRange } from '../../calendar/dates';
import * as S from './style';

const CATEGORIES: EventCategory[] = ['release', 'event', 'vacation', 'oncall', 'other'];

type Props = {
  calendar: FolioCalendar;
  mode?: CalendarMode;
  /** Shows the month or week toggle; without it the view stays as given. */
  onModeChange?: (mode: CalendarMode) => void;
  onSelectEvent?: (event: CalendarEvent) => void;
  /** Starts on this day; default today. */
  initial?: Date;
};

/** A calendar's month or week: its events colored by category and the Docket milestones
 * it shows, with buttons to move between months or weeks. */
export function CalendarView({
  calendar,
  mode = 'month',
  onModeChange,
  onSelectEvent,
  initial,
}: Props) {
  const { t, i18n } = useTranslation();
  const errorMessage = useErrorMessage();
  const [anchor, setAnchor] = useState(() => initial ?? new Date());
  const days = useMemo(() => viewDays(anchor, mode), [anchor, mode]);
  const range = viewRange(days);
  const agenda = useQuery({
    queryKey: calendarKeys.agenda(calendar.id, range.start, range.end),
    queryFn: () => fetchAgenda(calendar.id, range.start, range.end),
  });
  const events = useMemo(() => byDay(agenda.data?.events ?? []), [agenda.data]);
  const milestones = useMemo(() => {
    const out = new Map<string, CalendarMilestone[]>();
    for (const m of agenda.data?.milestones ?? []) out.set(m.due, [...(out.get(m.due) ?? []), m]);
    return out;
  }, [agenda.data]);

  const locale = i18n.language;
  const title = new Intl.DateTimeFormat(locale, { month: 'long', year: 'numeric' }).format(anchor);
  const weekday = new Intl.DateTimeFormat(locale, { weekday: 'short' });
  const clock = new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' });
  const today = dayKey(new Date());

  return (
    <S.Wrap $color={calendar.color} aria-label={calendar.name}>
      <S.Bar>
        <h3>
          {calendar.name} · {title}
        </h3>
        <Button size="sm" variant="ghost" onClick={() => setAnchor(new Date())}>
          {t('folio.calendar.today')}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          aria-label={t(`folio.calendar.previous.${mode}`)}
          onClick={() => setAnchor(shift(anchor, mode, -1))}
        >
          <ChevronLeft aria-hidden />
        </Button>
        <Button
          size="sm"
          variant="ghost"
          aria-label={t(`folio.calendar.next.${mode}`)}
          onClick={() => setAnchor(shift(anchor, mode, 1))}
        >
          <ChevronRight aria-hidden />
        </Button>
        {onModeChange && (
          <Button size="sm" onClick={() => onModeChange(mode === 'month' ? 'week' : 'month')}>
            {t(`folio.calendar.show.${mode === 'month' ? 'week' : 'month'}`)}
          </Button>
        )}
      </S.Bar>
      {agenda.isError && <S.Muted role="alert">{errorMessage(agenda.error)}</S.Muted>}
      <S.Grid $mode={mode}>
        {days.slice(0, 7).map((d) => (
          <S.Weekday key={`h-${dayKey(d)}`}>{weekday.format(d)}</S.Weekday>
        ))}
        {days.map((d) => {
          const key = dayKey(d);
          const outside = mode === 'month' && d.getMonth() !== anchor.getMonth();
          return (
            <S.Day key={key} $outside={outside} $today={key === today} data-day={key}>
              <S.DayNumber $today={key === today}>{d.getDate()}</S.DayNumber>
              {milestones.get(key)?.map((m) => (
                <S.Chip key={`${m.project}-${m.name}`} as="span" $category="milestone">
                  <Flag aria-hidden size={10} /> {m.project} · {m.name}
                </S.Chip>
              ))}
              {events.get(key)?.map((e) => (
                <S.Chip
                  key={e.id}
                  $category={e.category}
                  title={e.title}
                  onClick={onSelectEvent ? () => onSelectEvent(e) : undefined}
                  as={onSelectEvent ? 'button' : 'span'}
                >
                  {!e.all_day && <time>{clock.format(new Date(e.start_at))}</time>}
                  {e.title}
                </S.Chip>
              ))}
            </S.Day>
          );
        })}
      </S.Grid>
      <S.Legend>
        {CATEGORIES.map((c) => (
          <li key={c}>
            <S.Swatch $category={c} />
            {t(`folio.calendar.category.${c}`)}
          </li>
        ))}
        <li>
          <S.Swatch $category="milestone" />
          {t('folio.calendar.milestone')}
        </li>
      </S.Legend>
    </S.Wrap>
  );
}
