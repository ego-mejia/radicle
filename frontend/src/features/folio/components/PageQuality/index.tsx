import { useMutation, useQueryClient } from '@tanstack/react-query';
import { BadgeCheck, Eye, UserRoundPen } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { formatDate } from '../../../../lib/format';
import { folioKeys, type FolioNode } from '../../../../services/api/folio';
import { setNodeStatus, transferOwner } from '../../../../services/api/folioSocial';
import * as S from './style';

type Props = {
  node: FolioNode;
  /** The page's owner or an admin of its space: they verify it and hand it over. */
  canManage: boolean;
};

/** Keeping a page alive: verify it (until the space's expiry), mark it in review, or
 * transfer it to another owner. */
export function PageQuality({ node, canManage }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const client = useQueryClient();
  const [transferring, setTransferring] = useState(false);
  const [owner, setOwner] = useState('');
  const [ownerError, setOwnerError] = useState<string | null>(null);

  const refresh = (updated: FolioNode) => {
    client.setQueryData(folioKeys.node(node.id), updated);
    void client.invalidateQueries({ queryKey: folioKeys.versions(node.id) });
  };
  const status = useMutation({
    mutationFn: (next: 'in_review' | 'verified') => setNodeStatus(node.id, next),
    onSuccess: (updated) => {
      refresh(updated);
      toast(t(`folio.quality.done.${updated.status}`));
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const transfer = useMutation({
    mutationFn: () => transferOwner(node.id, owner),
    onSuccess: (updated) => {
      refresh(updated);
      setTransferring(false);
      toast(t('folio.quality.transferred', { handle: updated.metadata?.owner }));
    },
    onError: (e) => setOwnerError(errorMessage(e)),
  });

  if (node.version == null) return null;
  const until = node.status === 'verified' && node.verified_until;
  return (
    <S.Card aria-label={t('folio.quality.title')}>
      {until && <S.Note>{t('folio.quality.until', { date: formatDate(until) })}</S.Note>}
      {node.status === 'outdated' && <S.Warning>{t('folio.quality.outdated')}</S.Warning>}
      {canManage && (
        <S.Buttons>
          <Button size="sm" onClick={() => status.mutate('verified')} disabled={status.isPending}>
            <BadgeCheck aria-hidden />
            {node.status === 'verified'
              ? t('folio.quality.verifyAgain')
              : t('folio.quality.verify')}
          </Button>
          {node.status !== 'in_review' && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => status.mutate('in_review')}
              disabled={status.isPending}
            >
              <Eye aria-hidden />
              {t('folio.quality.review')}
            </Button>
          )}
          <Button size="sm" variant="ghost" onClick={() => setTransferring(true)}>
            <UserRoundPen aria-hidden />
            {t('folio.quality.transfer')}
          </Button>
        </S.Buttons>
      )}
      <Modal
        open={transferring}
        onOpenChange={setTransferring}
        title={t('folio.quality.transferTitle')}
        footer={
          <>
            <Button onClick={() => setTransferring(false)}>{t('common.cancel')}</Button>
            <Button
              variant="primary"
              disabled={!owner.trim() || transfer.isPending}
              onClick={() => {
                setOwnerError(null);
                transfer.mutate();
              }}
            >
              {t('folio.quality.transfer')}
            </Button>
          </>
        }
      >
        <Field
          label={t('folio.quality.newOwner')}
          hint={t('folio.quality.newOwnerHint')}
          error={ownerError}
        >
          <Input value={owner} onChange={(e) => setOwner(e.target.value)} placeholder="@ana" />
        </Field>
      </Modal>
    </S.Card>
  );
}
