import { useQuery } from '@tanstack/react-query';
import { ArrowRight } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Avatar } from '../../../../components/ui/Avatar';
import { Badge } from '../../../../components/ui/Badge';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { diffLines } from '../../../../lib/diff';
import { formatDateTime, relativeTime } from '../../../../lib/format';
import { fetchHistory, ticketKeys } from '../../../../services/api/tickets';
import type { HistoryEvent, Ticket } from '../../../../services/api/types';
import * as S from './style';

function show(value: unknown, t: (key: string) => string): string {
  if (value === null || value === undefined || value === '') return t('common.none');
  if (Array.isArray(value))
    return value.length ? value.map((v) => `#${v}`).join(' ') : t('common.none');
  if (typeof value === 'object') {
    const v = value as Record<string, unknown>;
    if ('status' in v) {
      const resolution = v.resolution
        ? ` (${t(`ticket.resolutions.${String(v.resolution)}`)})`
        : '';
      return `${String(v.status)}${resolution}`;
    }
    if ('label' in v && 'ticket' in v)
      return `${t(`ticket.linkLabels.${String(v.label)}`)} ${String(v.ticket)}`;
    if ('text' in v && 'checked' in v) return `${v.checked ? '☑' : '☐'} ${String(v.text)}`;
    if ('type' in v && 'title' in v) return String(v.title);
    return '';
  }
  return String(value);
}

function EventDetail({ event }: { event: HistoryEvent }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  if (event.field === 'description_md') {
    return (
      <>
        <S.Toggle onClick={() => setOpen(!open)}>
          {open ? t('history.hideDiff') : t('history.showDiff')}
        </S.Toggle>
        {open && (
          <S.Diff>
            {diffLines(String(event.old_value ?? ''), String(event.new_value ?? '')).map(
              (line, i) => (
                <S.DiffLine key={i} $kind={line.kind}>
                  {line.text}
                </S.DiffLine>
              ),
            )}
          </S.Diff>
        )}
      </>
    );
  }
  const hasOld = event.old_value !== null && event.old_value !== undefined;
  const hasNew = event.new_value !== null && event.new_value !== undefined;
  if (
    [
      'comment_added',
      'comment_edited',
      'comment_deleted',
      'created',
      'deleted',
      'restored',
    ].includes(event.event_type)
  ) {
    return null;
  }
  if (!hasOld && !hasNew) return null;
  return (
    <S.Change>
      {hasOld && <S.Old>{show(event.old_value, t)}</S.Old>}
      {hasOld && hasNew && <ArrowRight size={12} aria-hidden />}
      {hasNew && <S.New>{show(event.new_value, t)}</S.New>}
    </S.Change>
  );
}

/** Immutable history, newest first, with actor (agents marked) and old and new values. */
export function History({ ticket }: { ticket: Ticket }) {
  const { t } = useTranslation();
  const { data, isPending } = useQuery({
    queryKey: [...ticketKeys.history(ticket.key), ticket.version],
    queryFn: () => fetchHistory(ticket.key),
  });
  if (isPending) return <PageSpinner />;
  const events = data?.items ?? [];
  if (events.length === 0) return <p>{t('history.empty')}</p>;
  return (
    <S.List>
      {events.map((event) => {
        const field = event.field ? t(`ticket.fields.${fieldKey(event.field)}`) : '';
        return (
          <S.Event key={event.id}>
            <Avatar
              handle={event.actor.handle}
              name={event.actor.display_name}
              kind={event.actor.kind}
              size={22}
            />
            <div>
              <S.Line>
                <strong>{event.actor.display_name}</strong>
                {event.actor.kind === 'agent' && <Badge tone="accent">agent</Badge>}
                <span>
                  {t(`history.events.${event.event_type}`, { field: field.toLowerCase() })}
                </span>
                <time dateTime={event.created_at} title={formatDateTime(event.created_at)}>
                  {relativeTime(event.created_at)}
                </time>
              </S.Line>
              <EventDetail event={event} />
            </div>
          </S.Event>
        );
      })}
    </S.List>
  );
}

const FIELD_KEYS: Record<string, string> = {
  description_md: 'description',
  due_date: 'due',
  estimate_hours: 'estimate',
};

function fieldKey(field: string): string {
  return FIELD_KEYS[field] ?? field;
}
