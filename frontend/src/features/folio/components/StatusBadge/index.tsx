import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import type { Tone } from '../../../../components/ui/Badge/style';
import type { NodeStatus } from '../../../../services/api/folioSocial';

const TONE: Record<NodeStatus, Tone> = {
  draft: 'neutral',
  published: 'neutral',
  in_review: 'neutral',
  verified: 'accent',
  outdated: 'warning',
};

type Props = {
  status: NodeStatus;
  /** Cards only show the statuses that say something (in review, verified, outdated). */
  always?: boolean;
};

/** A page's quality state: Verified, In review, Outdated, and on the page itself any status. */
export function StatusBadge({ status, always = false }: Props) {
  const { t } = useTranslation();
  if (!status || (!always && (status === 'published' || status === 'draft'))) return null;
  return <Badge tone={TONE[status]}>{t(`folio.reader.status.${status}`)}</Badge>;
}
