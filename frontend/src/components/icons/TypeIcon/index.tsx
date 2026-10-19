import { Bean, Bug, SquareCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { TicketType } from '../../../services/api/types';
import { Wrap } from './style';

type Props = { type: TicketType; size?: number };

/** Task is a check, bug a bug, draft a seed (an idea that has not germinated yet). */
export function TypeIcon({ type, size = 14 }: Props) {
  const { t } = useTranslation();
  const Icon = type === 'bug' ? Bug : type === 'draft' ? Bean : SquareCheck;
  return (
    <Wrap $type={type} title={t(`ticket.types.${type}`)}>
      <Icon width={size} height={size} aria-label={t(`ticket.types.${type}`)} />
    </Wrap>
  );
}
