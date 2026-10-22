import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { formatDate } from '../../../../lib/format';
import type { FolioNode } from '../../../../services/api/folio';
import { RadiSuggestion } from '../RadiSuggestion';

type Props = { node: FolioNode };

const keyOf = (node: FolioNode) => `folio.radi.stale.${node.id}.${node.version ?? 0}`;

function dismissed(node: FolioNode): boolean {
  try {
    return window.localStorage.getItem(keyOf(node)) === '1';
  } catch {
    return false;
  }
}

/** Radi's "this page went stale" (RAD-57): a published page whose verification expired,
 * shown to whoever can edit it. Dismissing it hides it until the next version. */
export function StalePageSuggestion({ node }: Props) {
  const { t } = useTranslation();
  const [hidden, setHidden] = useState(() => dismissed(node));
  if (hidden || node.status !== 'outdated' || !node.can_edit || node.version == null) return null;
  const page = `${node.id}-${node.slug}`;
  const dismiss = () => {
    try {
      window.localStorage.setItem(keyOf(node), '1');
    } catch {
      // Private windows may refuse storage; it just shows again next time.
    }
    setHidden(true);
  };
  return (
    <RadiSuggestion
      title={t('folio.radi.staleTitle')}
      text={
        node.verified_until
          ? t('folio.radi.staleSince', { date: formatDate(node.verified_until) })
          : t('folio.radi.staleText')
      }
      actions={
        <>
          <Link to="/folio/p/$page/edit" params={{ page }}>
            {t('folio.radi.update')}
          </Link>
          <Link to="/folio/p/$page/history" params={{ page }}>
            {t('folio.radi.seeChanges')}
          </Link>
        </>
      }
      onDismiss={dismiss}
    />
  );
}
