import { Inbox } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CLASSIFICATIONS, type Classification, type Ticket } from '../../../../services/api/types';
import type { TicketActions } from '../../hooks/useTicket';
import * as S from './style';

type Props = { ticket: Ticket; actions: TicketActions; canTriage: boolean };

/** Inbox data: editable score on drafts, a "from the inbox" badge once converted. */
export function InboxInfo({ ticket, actions, canTriage }: Props) {
  const { t } = useTranslation();
  if (!ticket.origin) return null;
  const origin = t(`inbox.origins.${ticket.origin}`);
  const classification = ticket.classification
    ? t(`inbox.classifications.${ticket.classification}`)
    : '';
  if (ticket.type !== 'draft') {
    return (
      <S.Badge>
        <Inbox size={14} aria-hidden />
        {t('inbox.fromInboxDetail', { origin, classification })}
      </S.Badge>
    );
  }
  const score = (field: 'impact' | 'effort') => (
    <label>
      {t(`inbox.${field}`)}
      <select
        value={ticket[field] ?? ''}
        disabled={!canTriage}
        onChange={(e) =>
          actions.patch.mutate({ [field]: e.target.value ? Number(e.target.value) : null })
        }
      >
        <option value="">—</option>
        {[1, 2, 3, 4, 5].map((n) => (
          <option key={n} value={n}>
            {n}
          </option>
        ))}
      </select>
    </label>
  );
  return (
    <S.Box aria-label={t('inbox.title')}>
      <span>
        <Inbox size={14} aria-hidden /> {t('inbox.origin')}: <b>{origin}</b>
      </span>
      <label>
        {t('inbox.classification')}
        <select
          value={ticket.classification ?? 'idea'}
          disabled={!canTriage}
          onChange={(e) =>
            actions.patch.mutate({ classification: e.target.value as Classification })
          }
        >
          {CLASSIFICATIONS.map((c) => (
            <option key={c} value={c}>
              {t(`inbox.classifications.${c}`)}
            </option>
          ))}
        </select>
      </label>
      {score('impact')}
      {score('effort')}
      {(ticket.submitter_name || ticket.submitter_email) && (
        <span>
          {t('inbox.submitter')}: {ticket.submitter_name}{' '}
          {ticket.submitter_email && (
            <a href={`mailto:${ticket.submitter_email}`}>{ticket.submitter_email}</a>
          )}
        </span>
      )}
    </S.Box>
  );
}
