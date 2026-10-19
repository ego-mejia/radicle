import { Clock } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { formatHours } from '../../../../lib/duration';
import type { Ticket } from '../../../../services/api/types';
import type { TicketActions } from '../../hooks/useTicket';
import { InlineInput } from '../FieldsPanel/components/FieldRow';
import { LogTimeModal } from './components/LogTimeModal';
import * as S from './style';

type Props = { ticket: Ticket; actions: TicketActions; canEdit: boolean };

/** Estimate against time spent; turns to warning once spent passes the original estimate. */
export function TimeTracking({ ticket, actions, canEdit }: Props) {
  const { t } = useTranslation();
  const [logging, setLogging] = useState(false);
  const original = ticket.original_estimate_hours;
  const scale = Math.max(original ?? 0, ticket.estimate_hours ?? 0, ticket.spent_hours, 0.01);
  const over = original !== null && ticket.spent_hours > original;
  return (
    <S.Box aria-label={t('time.title')}>
      <S.Bar $over={over}>
        <span
          role="meter"
          aria-label={t('time.spent')}
          aria-valuemin={0}
          aria-valuemax={scale}
          aria-valuenow={ticket.spent_hours}
          style={{ width: `${Math.min(100, (ticket.spent_hours / scale) * 100)}%` }}
        />
        {original !== null && <S.Mark style={{ left: `${(original / scale) * 100}%` }} />}
      </S.Bar>
      <S.Numbers>
        <span>
          {t('time.spent')}: <strong>{formatHours(ticket.spent_hours)}</strong>
        </span>
        <span>
          {t('time.original')}: {formatHours(original)}
        </span>
      </S.Numbers>
      <S.Remaining>
        {t('time.remaining')}
        <InlineInput
          label={t('time.remaining')}
          type="number"
          value={ticket.remaining_hours?.toString() ?? ''}
          disabled={!canEdit}
          placeholder="—"
          onCommit={(value) =>
            actions.patch.mutate({ remaining_hours: value === '' ? null : Number(value) })
          }
        />
        {ticket.remaining_mode === 'manual' ? (
          canEdit && (
            <S.Link type="button" onClick={() => actions.patch.mutate({ remaining_mode: 'auto' })}>
              {t('time.backToAuto')}
            </S.Link>
          )
        ) : (
          <S.Auto>{t('time.auto')}</S.Auto>
        )}
      </S.Remaining>
      {over && <S.Warning role="status">{t('time.over')}</S.Warning>}
      {canEdit && (
        <Button size="sm" onClick={() => setLogging(true)}>
          <Clock />
          {t('time.log')}
        </Button>
      )}
      {logging && <LogTimeModal ticketKey={ticket.key} onClose={() => setLogging(false)} />}
    </S.Box>
  );
}
