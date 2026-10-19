import { ChevronDown, ChevronsDown, ChevronsUp, ChevronUp, Equal } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { Priority } from '../../../services/api/types';
import { Wrap } from './style';

const ICONS = {
  highest: ChevronsUp,
  high: ChevronUp,
  medium: Equal,
  low: ChevronDown,
  lowest: ChevronsDown,
};

export function PriorityIcon({ priority, size = 14 }: { priority: Priority; size?: number }) {
  const { t } = useTranslation();
  const Icon = ICONS[priority];
  const label = t(`ticket.priorities.${priority}`);
  return (
    <Wrap $priority={priority} title={label}>
      <Icon width={size} height={size} aria-label={label} />
    </Wrap>
  );
}
