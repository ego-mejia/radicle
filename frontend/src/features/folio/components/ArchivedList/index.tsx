import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Archive, ArchiveRestore } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { formatDate } from '../../../../lib/format';
import { fetchArchived, socialKeys, unarchiveNode } from '../../../../services/api/folioSocial';
import * as S from './style';

/** A space's Archived section: what was archived, by whom, with Restore. Folded by default. */
export function ArchivedList({ space, canRestore }: { space: string; canRestore: boolean }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const archived = useQuery({
    queryKey: socialKeys.archived(space),
    queryFn: () => fetchArchived(space),
  });
  const restore = useMutation({
    mutationFn: unarchiveNode,
    onSuccess: (node) => {
      void client.invalidateQueries({ queryKey: ['folio'] });
      toast(t('folio.organize.restored', { title: node.title }));
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });

  const items = archived.data ?? [];
  if (items.length === 0) return null;
  return (
    <S.Section>
      <S.Toggle type="button" aria-expanded={open} onClick={() => setOpen(!open)}>
        <Archive aria-hidden />
        {t('folio.organize.archivedSection', { count: items.length })}
      </S.Toggle>
      {open && (
        <S.List>
          {items.map((item) => (
            <li key={item.id}>
              <S.Text>
                <strong>{item.title}</strong>
                <small>
                  {t('folio.organize.archivedBy', {
                    who: item.archived_by ?? '—',
                    date: formatDate(item.archived_at.slice(0, 10)),
                  })}
                </small>
              </S.Text>
              {canRestore && (
                <Button
                  size="sm"
                  onClick={() => restore.mutate(item.id)}
                  disabled={restore.isPending}
                  aria-label={t('folio.organize.restoreTitle', { title: item.title })}
                >
                  <ArchiveRestore aria-hidden />
                  {t('folio.organize.restore')}
                </Button>
              )}
            </li>
          ))}
        </S.List>
      )}
    </S.Section>
  );
}
