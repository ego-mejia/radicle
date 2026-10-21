import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Archive, Copy, FolderInput, MoreHorizontal } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { Menu } from '../../../../components/ui/Menu';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { moveNode, nodePath } from '../../../../services/api/folio';
import { archiveNode, copyNode } from '../../../../services/api/folioSocial';
import { PlaceDialog, type Place } from './components/PlaceDialog';
import * as S from './style';

type Props = {
  node: { id: string; title: string; kind: string; space: string; can_delete?: boolean };
};

/** Move, Copy and Archive for a page, folder or post. Move and Archive need delete, so
 * they only show with can_delete; the API still has the last word. */
export function NodeMenu({ node }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const navigate = useNavigate();
  const client = useQueryClient();
  const [dialog, setDialog] = useState<'move' | 'copy' | 'archive' | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => client.invalidateQueries({ queryKey: ['folio'] });
  const close = () => {
    setDialog(null);
    setError(null);
  };
  const move = useMutation({
    mutationFn: (p: Place) => moveNode(node.id, { space: p.space, parent: p.parent }),
    onSuccess: (moved) => {
      close();
      void refresh();
      toast(t('folio.organize.moved', { space: moved.space }));
    },
    onError: (e) => setError(errorMessage(e)),
  });
  const copy = useMutation({
    mutationFn: (p: Place) =>
      copyNode(node.id, { space: p.space, parent: p.parent, include_children: p.includeChildren }),
    onSuccess: (made) => {
      close();
      void refresh();
      toast(t('folio.organize.copied'));
      void navigate({ to: '/folio/p/$page', params: { page: nodePath(made).split('/').pop()! } });
    },
    onError: (e) => setError(errorMessage(e)),
  });
  const archive = useMutation({
    mutationFn: () => archiveNode(node.id),
    onSuccess: () => {
      close();
      void refresh();
      toast(t('folio.organize.archived'));
      void navigate({ to: '/folio/s/$key', params: { key: node.space } });
    },
    onError: (e) => {
      close();
      toast(errorMessage(e), 'error');
    },
  });

  return (
    <>
      <Menu
        align="end"
        trigger={
          <S.Trigger type="button" aria-label={t('folio.organize.menu', { title: node.title })}>
            <MoreHorizontal aria-hidden />
          </S.Trigger>
        }
        items={[
          ...(node.can_delete === false
            ? []
            : [
                {
                  key: 'move',
                  label: t('folio.organize.moveEllipsis'),
                  icon: <FolderInput />,
                  onSelect: () => setDialog('move'),
                },
              ]),
          {
            key: 'copy',
            label: t('folio.organize.copyEllipsis'),
            icon: <Copy />,
            onSelect: () => setDialog('copy'),
          },
          ...(node.can_delete === false
            ? []
            : [
                { separator: true as const, key: 'sep' },
                {
                  key: 'archive',
                  label: t('folio.organize.archive'),
                  icon: <Archive />,
                  danger: true,
                  onSelect: () => setDialog('archive'),
                },
              ]),
        ]}
      />
      {(dialog === 'move' || dialog === 'copy') && (
        <PlaceDialog
          mode={dialog}
          node={node}
          open
          busy={move.isPending || copy.isPending}
          error={error}
          onClose={close}
          onSubmit={(place) => (dialog === 'move' ? move.mutate(place) : copy.mutate(place))}
        />
      )}
      <ConfirmDialog
        open={dialog === 'archive'}
        title={t('folio.organize.archiveTitle', { title: node.title })}
        message={t('folio.organize.archiveMessage')}
        confirmLabel={t('folio.organize.archive')}
        onConfirm={() => archive.mutate()}
        onCancel={close}
        danger
      />
    </>
  );
}
