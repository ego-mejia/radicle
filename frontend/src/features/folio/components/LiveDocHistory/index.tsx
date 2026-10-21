import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { RotateCcw } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  type FolioNode,
  fetchSnapshot,
  fetchSnapshots,
  folioKeys,
  restoreSnapshot,
} from '../../../../services/api/folio';
import { DocContent } from '../DocContent';
import type { DocNode } from '../DocContent/anchors';
import * as S from './style';

/** A live doc's history (Folio 2.5): a snapshot every 10 minutes, what it said and restore. */
export function LiveDocHistory({ node }: { node: FolioNode }) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const { data: snapshots } = useQuery({
    queryKey: folioKeys.snapshots(node.id),
    queryFn: () => fetchSnapshots(node.id),
  });
  const [picked, setPicked] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);
  const shown = picked ?? snapshots?.[0]?.id ?? null;
  const { data: snapshot } = useQuery({
    queryKey: folioKeys.snapshot(node.id, shown ?? ''),
    queryFn: () => fetchSnapshot(node.id, shown ?? ''),
    enabled: !!shown,
  });
  const restore = useMutation({
    mutationFn: (sid: string) => restoreSnapshot(node.id, sid),
    onSuccess: (made) => {
      setRestoring(false);
      setPicked(made.id);
      void queryClient.invalidateQueries({ queryKey: folioKeys.snapshots(node.id) });
      void queryClient.invalidateQueries({ queryKey: folioKeys.node(node.id) });
      toast(t('folio.liveHistory.restored'));
    },
    onError: (e) => {
      setRestoring(false);
      toast(errorMessage(e), 'error');
    },
  });

  if (!snapshots) return <PageSpinner />;
  const date = (iso: string) =>
    new Date(iso).toLocaleString(i18n.language, { dateStyle: 'medium', timeStyle: 'short' });

  return (
    <>
      <PageTitle
        title={t('folio.liveHistory.title')}
        subtitle={node.title}
        actions={
          <S.Back>
            <Link to="/folio/p/$page/edit" params={{ page: `${node.id}-${node.slug}` }}>
              {t('folio.liveHistory.back')}
            </Link>
          </S.Back>
        }
      />
      {snapshots.length === 0 ? (
        <S.Muted>{t('folio.liveHistory.none')}</S.Muted>
      ) : (
        <S.Layout>
          <S.List aria-label={t('folio.liveHistory.snapshots')}>
            {snapshots.map((s) => (
              <li key={s.id}>
                <S.Item
                  type="button"
                  aria-pressed={s.id === shown}
                  $selected={s.id === shown}
                  onClick={() => setPicked(s.id)}
                >
                  <strong>{date(s.created_at)}</strong>
                  <S.Meta>
                    {s.authors.length ? s.authors.join(', ') : t('folio.liveHistory.nobody')}
                  </S.Meta>
                </S.Item>
              </li>
            ))}
          </S.List>
          <S.Panel>
            {snapshot ? (
              <>
                <S.PanelTop>
                  <h2>{date(snapshot.created_at)}</h2>
                  {shown !== snapshots[0]?.id && (
                    <Button size="sm" onClick={() => setRestoring(true)}>
                      <RotateCcw aria-hidden />
                      {t('folio.liveHistory.restore')}
                    </Button>
                  )}
                </S.PanelTop>
                <DocContent doc={snapshot.content_json as DocNode} />
              </>
            ) : (
              <PageSpinner />
            )}
          </S.Panel>
        </S.Layout>
      )}
      <ConfirmDialog
        open={restoring}
        danger={false}
        title={t('folio.liveHistory.restoreTitle')}
        message={t('folio.liveHistory.restoreText')}
        confirmLabel={t('folio.liveHistory.restoreConfirm')}
        onConfirm={() => shown && restore.mutate(shown)}
        onCancel={() => setRestoring(false)}
      />
    </>
  );
}
