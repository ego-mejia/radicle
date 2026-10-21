import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ListChecks } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Modal } from '../../../../components/ui/Modal';
import { useToast } from '../../../../hooks/useToast';
import { isApiError } from '../../../../services/api/client';
import {
  createBuildSpecTickets,
  fetchBuildSpecItems,
  ticketKeys,
  type BuildSpecItem,
} from '../../../../services/api/folioTickets';
import { useTicketTarget } from '../../hooks/useTicketTarget';
import { TicketTargetFields } from '../TicketTargetFields';
import * as S from './style';

/** "Create tickets" on a build spec (Folio 4.3): the button and its wizard. */
export function BuildSpecTickets({ nodeId }: { nodeId: string }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        <ListChecks aria-hidden />
        {t('folio.buildSpec.button')}
      </button>
      {open && <Wizard nodeId={nodeId} onClose={() => setOpen(false)} />}
    </>
  );
}

function Wizard({ nodeId, onClose }: { nodeId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const target = useTicketTarget();
  // Deliverables left out by hand; the rest of the new ones are sent.
  const [skipped, setSkipped] = useState<Set<string>>(new Set());
  const items = useQuery({
    queryKey: ticketKeys.buildSpec(nodeId),
    queryFn: () => fetchBuildSpecItems(nodeId),
  });
  const fresh = (items.data ?? []).filter((i) => !i.linked);
  const chosen = fresh.filter((i) => !skipped.has(i.key)).map((i) => i.key);
  const create = useMutation({
    mutationFn: () =>
      createBuildSpecTickets(nodeId, {
        project: target.project,
        keys: chosen,
        type: target.type,
        area: target.area || null,
        milestone: target.milestone || null,
      }),
    onSuccess: (made) => {
      void queryClient.invalidateQueries({ queryKey: ticketKeys.buildSpec(nodeId) });
      void queryClient.invalidateQueries({ queryKey: ticketKeys.links(nodeId) });
      toast(t('folio.buildSpec.created', { count: made.length }));
      onClose();
    },
  });
  const toggle = (key: string) =>
    setSkipped((now) => {
      const next = new Set(now);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  return (
    <Modal
      open
      onOpenChange={(o) => !o && onClose()}
      title={t('folio.buildSpec.title')}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            disabled={!target.project || chosen.length === 0 || create.isPending}
            onClick={() => create.mutate()}
          >
            {t('folio.buildSpec.create', { count: chosen.length })}
          </Button>
        </>
      }
    >
      <S.Form>
        <S.Intro>{t('folio.buildSpec.intro')}</S.Intro>
        {items.isError ? (
          <S.Error role="alert">
            {isApiError(items.error) ? items.error.message : t('folio.buildSpec.failed')}
          </S.Error>
        ) : items.data?.length === 0 ? (
          <S.Intro>{t('folio.buildSpec.empty')}</S.Intro>
        ) : (
          <S.List aria-label={t('folio.buildSpec.items')}>
            {(items.data ?? []).map((item) => (
              <Row
                key={item.key}
                item={item}
                checked={!item.linked && !skipped.has(item.key)}
                onToggle={() => toggle(item.key)}
              />
            ))}
          </S.List>
        )}
        <TicketTargetFields target={target} />
        {create.error ? (
          <S.Error role="alert">
            {isApiError(create.error) ? create.error.message : t('folio.buildSpec.failed')}
          </S.Error>
        ) : null}
      </S.Form>
    </Modal>
  );
}

function Row({
  item,
  checked,
  onToggle,
}: {
  item: BuildSpecItem;
  checked: boolean;
  onToggle: () => void;
}) {
  const { t } = useTranslation();
  return (
    <S.Item>
      <input
        type="checkbox"
        checked={checked}
        disabled={item.linked}
        onChange={onToggle}
        aria-label={`${item.key} ${item.title}`}
      />
      <S.Key>{item.key}</S.Key>
      <S.Body>
        <S.Title>{item.title}</S.Title>
        <S.Muted>{t('folio.buildSpec.criteria', { count: item.criteria.length })}</S.Muted>
      </S.Body>
      {item.linked && (
        <S.Muted>
          {item.ticket
            ? t('folio.buildSpec.already', { key: item.ticket.key })
            : t('folio.tickets.restricted')}
        </S.Muted>
      )}
    </S.Item>
  );
}
