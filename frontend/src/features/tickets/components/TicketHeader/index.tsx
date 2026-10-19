import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Copy, FolderInput, Link2, MoreHorizontal, Repeat, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { TypeIcon } from '../../../../components/icons/TypeIcon';
import { Badge, TicketKey } from '../../../../components/ui/Badge';
import { IconButton } from '../../../../components/ui/Button';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { Menu } from '../../../../components/ui/Menu';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useTicketCommand } from '../../../../hooks/useTicketCommand';
import { useToast } from '../../../../hooks/useToast';
import { deleteTicket, ticketKeys } from '../../../../services/api/tickets';
import type { Ticket } from '../../../../services/api/types';
import type { TicketActions } from '../../hooks/useTicket';
import { ChangeTypeModal } from '../ChangeTypeModal';
import { CloneModal } from '../CloneModal';
import { MoveModal } from '../MoveModal';
import { StatusButton } from '../StatusButton';
import { VoteButton } from '../VoteButton';
import * as S from './style';

type Props = { ticket: Ticket; actions: TicketActions; canEdit: boolean; isAdmin: boolean };

export function TicketHeader({ ticket, actions, canEdit, isAdmin }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(ticket.title);
  const [changingType, setChangingType] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [dialog, setDialog] = useState<'clone' | 'move' | null>(null);
  const remove = useMutation({
    mutationFn: () => deleteTicket(ticket.key),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ticketKeys.all });
      await navigate({ to: '/p/$key/board', params: { key: ticket.project }, search: {} });
    },
    onError: (error) => toast(errorMessage(error), 'error'),
  });

  useTicketCommand(
    'edit-title',
    () => {
      setTitle(ticket.title);
      setEditing(true);
    },
    canEdit,
  );

  const saveTitle = () => {
    setEditing(false);
    const next = title.trim();
    if (next && next !== ticket.title) actions.patch.mutate({ title: next });
    else setTitle(ticket.title);
  };

  const copyLink = async () => {
    await navigator.clipboard?.writeText(`${window.location.origin}/t/${ticket.key}`);
    toast(t('ticket.menu.linkCopied'));
  };

  return (
    <S.Header>
      <S.Top>
        <TypeIcon type={ticket.type} size={16} />
        <TicketKey>{ticket.key}</TicketKey>
        <StatusButton ticket={ticket} actions={actions} canEdit={canEdit} />
        {ticket.blocked && <Badge tone="danger">{t('ticket.blocked')}</Badge>}
        <S.Spacer />
        <VoteButton ticket={ticket} canVote={canEdit} />
        <Menu
          align="end"
          trigger={
            <IconButton label={t('common.more')}>
              <MoreHorizontal />
            </IconButton>
          }
          items={[
            {
              key: 'type',
              label: t('ticket.menu.changeType'),
              icon: <Repeat />,
              disabled: !canEdit,
              onSelect: () => setChangingType(true),
            },
            {
              key: 'clone',
              label: t('ticket.menu.clone'),
              icon: <Copy />,
              disabled: !canEdit,
              onSelect: () => setDialog('clone'),
            },
            ...(isAdmin
              ? [
                  {
                    key: 'move',
                    label: t('ticket.menu.move'),
                    icon: <FolderInput />,
                    onSelect: () => setDialog('move'),
                  },
                ]
              : []),
            {
              key: 'copy',
              label: t('ticket.menu.copyLink'),
              icon: <Link2 />,
              onSelect: () => void copyLink(),
            },
            ...(isAdmin
              ? [
                  { separator: true as const, key: 'sep' },
                  {
                    key: 'delete',
                    label: t('ticket.menu.delete'),
                    icon: <Trash2 />,
                    danger: true,
                    onSelect: () => setConfirmDelete(true),
                  },
                ]
              : []),
          ]}
        />
      </S.Top>
      {editing ? (
        <S.TitleInput
          value={title}
          autoFocus
          aria-label={t('ticket.fields.title')}
          maxLength={255}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={saveTitle}
          onKeyDown={(e) => {
            if (e.key === 'Enter') saveTitle();
            if (e.key === 'Escape') {
              setTitle(ticket.title);
              setEditing(false);
            }
          }}
        />
      ) : (
        <S.TitleButton
          onClick={() => canEdit && (setTitle(ticket.title), setEditing(true))}
          disabled={!canEdit}
          aria-label={t('ticket.editTitle')}
        >
          <S.Title>{ticket.title}</S.Title>
        </S.TitleButton>
      )}
      <ConfirmDialog
        open={confirmDelete}
        title={t('ticket.menu.delete')}
        message={t('ticket.deleteConfirm', { key: ticket.key })}
        confirmLabel={t('common.delete')}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => {
          setConfirmDelete(false);
          remove.mutate();
        }}
      />
      {dialog === 'clone' && <CloneModal ticket={ticket} onClose={() => setDialog(null)} />}
      {dialog === 'move' && <MoveModal ticket={ticket} onClose={() => setDialog(null)} />}
      {changingType && (
        <ChangeTypeModal ticket={ticket} actions={actions} onClose={() => setChangingType(false)} />
      )}
    </S.Header>
  );
}
