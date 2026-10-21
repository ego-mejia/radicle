import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { CalendarPlus, Link2, Plus, Settings } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { fetchSpace, folioKeys } from '../../../../services/api/folio';
import {
  type CalendarEvent,
  calendarKeys,
  feedUrl,
  fetchCalendars,
} from '../../../../services/api/folioCalendars';
import type { CalendarMode } from '../../calendar/dates';
import { CalendarEventDialog } from '../CalendarEventDialog';
import { CalendarSettingsDialog } from '../CalendarSettingsDialog';
import { CalendarView } from '../CalendarView';
import * as S from './style';

type Dialog =
  { kind: 'event'; event: CalendarEvent | null } | { kind: 'settings'; isNew: boolean } | null;

/** A space's calendars (Folio 5.8): one at a time in month or week view, with buttons to
 * add events, subscribe to its feed and, for space admins, manage calendars. */
export function CalendarsPage({ spaceKey }: { spaceKey: string }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [chosen, setChosen] = useState<string | null>(null);
  const [mode, setMode] = useState<CalendarMode>('month');
  const [dialog, setDialog] = useState<Dialog>(null);
  const space = useQuery({
    queryKey: folioKeys.space(spaceKey),
    queryFn: () => fetchSpace(spaceKey),
  });
  const calendars = useQuery({
    queryKey: calendarKeys.list(spaceKey),
    queryFn: () => fetchCalendars(spaceKey),
  });

  if (space.isPending || calendars.isPending) return <PageSpinner />;
  if (space.isError || calendars.isError)
    return (
      <EmptyState
        title={t('folio.space.notFound')}
        text={errorMessage(space.error ?? calendars.error)}
      />
    );
  const isAdmin = space.data.permissions.includes('admin');
  const current = calendars.data.find((c) => c.id === chosen) ?? calendars.data[0] ?? null;
  const close = (open: boolean) => !open && setDialog(null);

  return (
    <S.Page>
      <S.Header>
        <h1>
          <Link to="/folio/s/$key" params={{ key: spaceKey }}>
            {space.data.name}
          </Link>{' '}
          · {t('folio.calendar.title')}
        </h1>
        {current && (
          <Button
            onClick={async () => {
              await navigator.clipboard?.writeText(feedUrl(current));
              toast(t('folio.calendar.feed.copied'));
            }}
          >
            <Link2 aria-hidden />
            {t('folio.calendar.feed.copy')}
          </Button>
        )}
        {current?.can_manage && (
          <Button onClick={() => setDialog({ kind: 'settings', isNew: false })}>
            <Settings aria-hidden />
            {t('folio.calendar.settings.title')}
          </Button>
        )}
        {isAdmin && (
          <Button onClick={() => setDialog({ kind: 'settings', isNew: true })}>
            <CalendarPlus aria-hidden />
            {t('folio.calendar.settings.new')}
          </Button>
        )}
        {current?.can_add && (
          <Button variant="primary" onClick={() => setDialog({ kind: 'event', event: null })}>
            <Plus aria-hidden />
            {t('folio.calendar.event.new')}
          </Button>
        )}
      </S.Header>

      {calendars.data.length > 1 && (
        <S.Tabs role="tablist">
          {calendars.data.map((c) => (
            <Button
              key={c.id}
              size="sm"
              role="tab"
              aria-selected={c.id === current?.id}
              variant={c.id === current?.id ? 'primary' : 'ghost'}
              onClick={() => setChosen(c.id)}
            >
              {c.name}
            </Button>
          ))}
        </S.Tabs>
      )}

      {current ? (
        <CalendarView
          key={current.id}
          calendar={current}
          mode={mode}
          onModeChange={setMode}
          onSelectEvent={(event) => setDialog({ kind: 'event', event })}
        />
      ) : (
        <EmptyState
          title={t('folio.calendar.empty')}
          text={t(isAdmin ? 'folio.calendar.emptyAdmin' : 'folio.calendar.emptyReader')}
        />
      )}

      {dialog?.kind === 'event' && current && (
        <CalendarEventDialog
          calendarId={current.id}
          event={dialog.event}
          open
          onOpenChange={close}
        />
      )}
      {dialog?.kind === 'settings' && (
        <CalendarSettingsDialog
          space={spaceKey}
          calendar={dialog.isNew ? null : current}
          open
          onOpenChange={close}
          onSaved={(saved) => setChosen(saved?.id ?? null)}
        />
      )}
    </S.Page>
  );
}
