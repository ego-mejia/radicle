import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { queryDocs } from '../../../../services/api/folio';
import { sectionQuery } from '../../sections';
import { RadiSuggestion } from '../RadiSuggestion';

const keyOf = (space: string, ids: string[]) => `folio.radi.staleDocs.${space}.${ids.join(',')}`;

function dismissed(key: string): boolean {
  try {
    return window.localStorage.getItem(key) === '1';
  } catch {
    return false;
  }
}

/** Radi's notice on the Docs section (RAD-57): reference pages of the space whose
 * verification expired, oldest first. Dismissing it hides it until another page goes
 * stale. Shown only to people who can write in the space. */
export function StaleDocsNotice({ space }: { space: string }) {
  const { t } = useTranslation();
  const [hiddenKey, setHiddenKey] = useState<string | null>(null);
  const stale = useQuery({
    queryKey: ['folio', 'section', space, 'docs', 'stale'],
    queryFn: async () =>
      (await queryDocs(sectionQuery(space, 'docs', 'status = outdated', 'updated ASC'), 20)).items,
  });
  const docs = stale.data ?? [];
  if (!docs.length) return null;
  const key = keyOf(
    space,
    docs.map((d) => d.id),
  );
  if (hiddenKey === key || dismissed(key)) return null;
  const first = docs[0];
  const page = `${first.id}-${first.slug}`;
  const dismiss = () => {
    try {
      window.localStorage.setItem(key, '1');
    } catch {
      // Private windows may refuse storage; it just shows again next time.
    }
    setHiddenKey(key);
  };
  return (
    <RadiSuggestion
      title={t('folio.radi.staleDocsTitle', { count: docs.length })}
      text={t('folio.radi.staleDocsText', { title: first.title })}
      actions={
        <>
          <Link to="/folio/p/$page/edit" params={{ page }}>
            {t('folio.radi.update')}
          </Link>
          <Link to="/folio/p/$page" params={{ page }}>
            {t('folio.radi.seePage')}
          </Link>
        </>
      }
      onDismiss={dismiss}
    />
  );
}
