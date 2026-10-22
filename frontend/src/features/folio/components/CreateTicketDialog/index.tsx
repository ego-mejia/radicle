import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useToast } from '../../../../hooks/useToast';
import { isApiError } from '../../../../services/api/client';
import { createTicketFromText, ticketKeys } from '../../../../services/api/folioTickets';
import { useTicketTarget } from '../../hooks/useTicketTarget';
import { TicketTargetFields } from '../TicketTargetFields';
import * as S from './style';

type Props = {
  nodeId: string;
  /** The selection or action item the ticket is made from. */
  text: string;
  /** The heading anchor of its section, so the ticket links right there. */
  anchor: string | null;
  onClose: () => void;
};

const firstLine = (text: string) => (text.trim().split('\n')[0] ?? '').slice(0, 120);

/** Create a Docket ticket from text in a doc (Folio 4.2): the ticket quotes it and links
 * back to its section, and the doc lists it among its tickets. */
export function CreateTicketDialog({ nodeId, text, anchor, onClose }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(() => firstLine(text));
  const target = useTicketTarget(nodeId);
  const chosen = target.project;
  const create = useMutation({
    mutationFn: () =>
      createTicketFromText(nodeId, {
        text,
        anchor,
        project: chosen,
        title: title.trim() || null,
        type: target.type,
        area: target.area || null,
        milestone: target.milestone || null,
      }),
    onSuccess: (link) => {
      void queryClient.invalidateQueries({ queryKey: ticketKeys.links(nodeId) });
      toast(t('folio.tickets.created', { key: link.ticket?.key ?? '' }));
      onClose();
    },
  });

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={t('folio.tickets.create')}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            disabled={!chosen || create.isPending}
            onClick={() => create.mutate()}
          >
            {t('folio.tickets.createButton')}
          </Button>
        </>
      }
    >
      <S.Form>
        <S.Quote>“{text.trim()}”</S.Quote>
        <Field label={t('folio.tickets.title')}>
          <Input value={title} maxLength={255} onChange={(e) => setTitle(e.target.value)} />
        </Field>
        <TicketTargetFields target={target} />
        {create.error ? (
          <S.Error role="alert">
            {isApiError(create.error) ? create.error.message : t('folio.tickets.createFailed')}
          </S.Error>
        ) : null}
      </S.Form>
    </Modal>
  );
}
