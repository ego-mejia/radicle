import { CheckCircle2, Copy, Eye, MoreHorizontal, XCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Badge, TicketKey } from '../../../../components/ui/Badge';
import { IconButton } from '../../../../components/ui/Button';
import { Menu } from '../../../../components/ui/Menu';
import { relativeTime } from '../../../../lib/format';
import type { InboxTab, TicketSummary } from '../../../../services/api/types';
import * as S from './style';

export type TriageAction = 'review' | 'approve' | 'duplicate' | 'discard';
const SCORES = [1, 2, 3, 4, 5];

type Props = {
  items: TicketSummary[];
  tab: InboxTab;
  canTriage: boolean;
  onOpen: (key: string) => void;
  onScore: (key: string, field: 'impact' | 'effort', value: number | null) => void;
  onAction: (action: TriageAction, ticket: TicketSummary) => void;
};

/** Drafts with classification, origin, votes, score and triage actions. */
export function InboxTable({ items, tab, canTriage, onOpen, onScore, onAction }: Props) {
  const { t } = useTranslation();
  const open = tab === 'new' || tab === 'in_review';
  const score = (ticket: TicketSummary, field: 'impact' | 'effort') => (
    <select
      aria-label={t(`inbox.${field}For`, { key: ticket.key })}
      value={ticket[field] ?? ''}
      disabled={!canTriage || !open}
      onChange={(e) => onScore(ticket.key, field, e.target.value ? Number(e.target.value) : null)}
    >
      <option value="">—</option>
      {SCORES.map((n) => (
        <option key={n} value={n}>
          {n}
        </option>
      ))}
    </select>
  );
  return (
    <S.Table>
      <thead>
        <tr>
          <th scope="col">{t('inbox.cols.key')}</th>
          <th scope="col">{t('inbox.cols.title')}</th>
          <th scope="col">{t('inbox.classification')}</th>
          <th scope="col">{t('inbox.origin')}</th>
          <th scope="col">🙋</th>
          <th scope="col">{t('inbox.impact')}</th>
          <th scope="col">{t('inbox.effort')}</th>
          <th scope="col">{t('inbox.cols.age')}</th>
          <th scope="col">{t('inbox.cols.status')}</th>
          {canTriage && open && <th scope="col" aria-label={t('inbox.cols.actions')} />}
        </tr>
      </thead>
      <tbody>
        {items.map((ticket) => (
          <tr key={ticket.key} data-testid={`inbox-${ticket.key}`}>
            <td>
              <TicketKey>{ticket.key}</TicketKey>
            </td>
            <td>
              <S.Title type="button" onClick={() => onOpen(ticket.key)}>
                {ticket.title}
              </S.Title>
            </td>
            <td>
              {ticket.classification && (
                <S.Class $kind={ticket.classification}>
                  {t(`inbox.classifications.${ticket.classification}`)}
                </S.Class>
              )}
            </td>
            <td>{ticket.origin && <Badge>{t(`inbox.origins.${ticket.origin}`)}</Badge>}</td>
            <td>{ticket.vote_count}</td>
            <td>{score(ticket, 'impact')}</td>
            <td>{score(ticket, 'effort')}</td>
            <td>{ticket.created_at ? relativeTime(ticket.created_at) : ''}</td>
            <td>{ticket.status.name}</td>
            {canTriage && open && (
              <td>
                <Menu
                  align="end"
                  trigger={
                    <IconButton label={t('inbox.actionsFor', { key: ticket.key })}>
                      <MoreHorizontal />
                    </IconButton>
                  }
                  items={[
                    ...(tab === 'new'
                      ? [
                          {
                            key: 'review',
                            label: t('inbox.review'),
                            icon: <Eye />,
                            onSelect: () => onAction('review', ticket),
                          },
                        ]
                      : []),
                    {
                      key: 'approve',
                      label: t('inbox.approve'),
                      icon: <CheckCircle2 />,
                      onSelect: () => onAction('approve', ticket),
                    },
                    {
                      key: 'duplicate',
                      label: t('inbox.markDuplicate'),
                      icon: <Copy />,
                      onSelect: () => onAction('duplicate', ticket),
                    },
                    {
                      key: 'discard',
                      label: t('inbox.discard'),
                      icon: <XCircle />,
                      danger: true,
                      onSelect: () => onAction('discard', ticket),
                    },
                  ]}
                />
              </td>
            )}
          </tr>
        ))}
      </tbody>
    </S.Table>
  );
}
