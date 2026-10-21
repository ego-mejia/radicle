import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { RotateCcw } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useMe } from '../../../../hooks/useMe';
import { useToast } from '../../../../hooks/useToast';
import {
  type FolioVersion,
  fetchDiff,
  fetchFolioMe,
  fetchNode,
  fetchVersions,
  folioKeys,
  restoreVersion,
} from '../../../../services/api/folio';
import { DiffView } from '../DiffView';
import * as S from './style';

type Props = { nodeId: string; from?: number; to?: number };

/** Default comparison: the published version against the one before it. */
function defaults(versions: FolioVersion[], from?: number, to?: number) {
  const latest = versions[0]?.number ?? 1;
  const right = to ?? latest;
  return { from: from ?? Math.max(1, right - 1), to: right };
}

/** A page's history (Folio 1.3): every version, the diff of any two and restore. */
export function PageHistory({ nodeId, from, to }: Props) {
  const { t, i18n } = useTranslation();
  const me = useMe();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const { data: folio } = useQuery({ queryKey: folioKeys.me, queryFn: fetchFolioMe });
  const { data: node } = useQuery({
    queryKey: folioKeys.node(nodeId),
    queryFn: () => fetchNode(nodeId),
  });
  const { data: versions } = useQuery({
    queryKey: folioKeys.versions(nodeId),
    queryFn: () => fetchVersions(nodeId),
  });
  const [picked, setPicked] = useState<{ from?: number; to?: number }>({ from, to });
  const [restoring, setRestoring] = useState<number | null>(null);
  const range = defaults(versions ?? [], picked.from, picked.to);
  const comparable = (versions?.length ?? 0) > 1 && range.from !== range.to;
  const { data: diff } = useQuery({
    queryKey: folioKeys.diff(nodeId, range.from, range.to),
    queryFn: () => fetchDiff(nodeId, range.from, range.to),
    enabled: comparable,
  });
  const restore = useMutation({
    mutationFn: (number: number) => restoreVersion(nodeId, number),
    onSuccess: (version) => {
      setRestoring(null);
      setPicked({ to: version.number });
      void queryClient.invalidateQueries({ queryKey: folioKeys.node(nodeId) });
      void queryClient.invalidateQueries({ queryKey: folioKeys.versions(nodeId) });
      toast(t('folio.history.restored', { number: version.number }));
    },
    onError: (e) => {
      setRestoring(null);
      toast(errorMessage(e), 'error');
    },
  });

  if (!node || !versions) return <PageSpinner />;
  // People who can write may restore; the API still checks the page's permissions.
  const canRestore = me.kind === 'human' && !!folio && folio.role !== 'reader';
  const date = (iso: string) =>
    new Date(iso).toLocaleString(i18n.language, { dateStyle: 'medium', timeStyle: 'short' });

  return (
    <>
      <PageTitle
        title={t('folio.history.title')}
        subtitle={node.title}
        actions={
          <S.Back>
            <Link to="/folio/p/$page" params={{ page: `${node.id}-${node.slug}` }}>
              {t('folio.history.back')}
            </Link>
          </S.Back>
        }
      />
      {versions.length === 0 ? (
        <S.Muted>{t('folio.history.none')}</S.Muted>
      ) : (
        <S.Layout>
          <S.List aria-label={t('folio.history.versions')}>
            {versions.map((v) => (
              <S.Item key={v.number} $selected={v.number === range.from || v.number === range.to}>
                <S.Top>
                  <S.Number>v{v.number}</S.Number>
                  <strong>{v.title}</strong>
                  {v.number === node.version && (
                    <Badge tone="accent">{t('folio.history.live')}</Badge>
                  )}
                </S.Top>
                <S.Meta>
                  {t('folio.history.by', { author: v.author, date: date(v.created_at) })}
                  {v.approved_by && ` · ${t('folio.history.approvedBy', { who: v.approved_by })}`}
                  {v.restored_from &&
                    ` · ${t('folio.history.restoredFrom', { number: v.restored_from })}`}
                </S.Meta>
                {v.change_note && <S.Note>{v.change_note}</S.Note>}
                <S.Picks>
                  <label>
                    <input
                      type="radio"
                      name="from"
                      checked={range.from === v.number}
                      onChange={() => setPicked({ ...picked, from: v.number, to: range.to })}
                    />
                    {t('folio.history.compareFrom')}
                  </label>
                  <label>
                    <input
                      type="radio"
                      name="to"
                      checked={range.to === v.number}
                      onChange={() => setPicked({ ...picked, from: range.from, to: v.number })}
                    />
                    {t('folio.history.compareTo')}
                  </label>
                  {canRestore && v.number !== node.version && (
                    <Button size="sm" variant="ghost" onClick={() => setRestoring(v.number)}>
                      <RotateCcw aria-hidden />
                      {t('folio.history.restore', { number: v.number })}
                    </Button>
                  )}
                </S.Picks>
              </S.Item>
            ))}
          </S.List>
          <S.Panel>
            <h2>{t('folio.history.comparing', range)}</h2>
            {!comparable && <S.Muted>{t('folio.history.pickTwo')}</S.Muted>}
            {comparable && (diff ? <DiffView diff={diff} /> : <PageSpinner />)}
          </S.Panel>
        </S.Layout>
      )}
      <ConfirmDialog
        open={restoring !== null}
        danger={false}
        title={t('folio.history.restoreTitle', { number: restoring })}
        message={t('folio.history.restoreText', { number: restoring })}
        confirmLabel={t('folio.history.restoreConfirm')}
        onConfirm={() => restoring !== null && restore.mutate(restoring)}
        onCancel={() => setRestoring(null)}
      />
    </>
  );
}
