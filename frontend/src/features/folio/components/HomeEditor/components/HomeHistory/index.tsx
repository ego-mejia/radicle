import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../../../components/ui/Badge';
import { Button } from '../../../../../../components/ui/Button';
import { ConfirmDialog } from '../../../../../../components/ui/ConfirmDialog';
import { PageSpinner } from '../../../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../../../hooks/useErrorMessage';
import { useToast } from '../../../../../../hooks/useToast';
import { formatDateTime } from '../../../../../../lib/format';
import {
  type HomeLayoutVersion,
  fetchHomeHistory,
  folioHomeKey,
  homeEditorKeys,
  restoreHome,
} from '../../../../../../services/api/folio';
import * as S from './style';

/** Every published layout, newest first; restoring one publishes it again. */
export function HomeHistory({ onRestored }: { onRestored: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [restoring, setRestoring] = useState<HomeLayoutVersion | null>(null);
  const { data: versions } = useQuery({
    queryKey: homeEditorKeys.history,
    queryFn: fetchHomeHistory,
  });
  const restore = useMutation({
    mutationFn: (v: HomeLayoutVersion) => restoreHome(v.id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: homeEditorKeys.history });
      void queryClient.invalidateQueries({ queryKey: homeEditorKeys.draft });
      void queryClient.invalidateQueries({ queryKey: folioHomeKey });
      toast(t('folio.homeEditor.restored'));
      onRestored();
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const when = (v: HomeLayoutVersion) => (v.published_at ? formatDateTime(v.published_at) : '');

  if (!versions) return <PageSpinner />;
  return (
    <S.Wrap aria-label={t('folio.homeEditor.history')}>
      {versions.length === 0 ? (
        <S.Muted>{t('folio.homeEditor.noHistory')}</S.Muted>
      ) : (
        <S.List>
          {versions.map((v) => (
            <S.Row key={v.id}>
              <S.Text>
                <strong>{when(v)}</strong>
                <small>
                  {t('folio.homeEditor.versionMeta', {
                    who: v.published_by ? `@${v.published_by}` : '—',
                    count: v.layout.blocks.length,
                  })}
                </small>
              </S.Text>
              {v.is_active ? (
                <Badge tone="accent">{t('folio.homeEditor.live')}</Badge>
              ) : (
                <Button size="sm" onClick={() => setRestoring(v)} disabled={restore.isPending}>
                  {t('folio.homeEditor.restore')}
                </Button>
              )}
            </S.Row>
          ))}
        </S.List>
      )}
      <ConfirmDialog
        open={Boolean(restoring)}
        title={t('folio.homeEditor.restoreTitle', { when: restoring ? when(restoring) : '' })}
        message={t('folio.homeEditor.restoreConfirm')}
        confirmLabel={t('folio.homeEditor.restore')}
        onConfirm={() => {
          if (restoring) restore.mutate(restoring);
          setRestoring(null);
        }}
        onCancel={() => setRestoring(null)}
      />
    </S.Wrap>
  );
}
