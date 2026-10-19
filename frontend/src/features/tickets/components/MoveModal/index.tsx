import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Select } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useMe } from '../../../../hooks/useMe';
import { moveTicket } from '../../../../services/api/bulk';
import { ticketKeys } from '../../../../services/api/tickets';
import type { Ticket } from '../../../../services/api/types';
import { useProject } from '../../../projects/hooks/useProject';
import * as S from './style';

/** Move to another project, mapping the area and the status when they do not exist there. */
export function MoveModal({ ticket, onClose }: { ticket: Ticket; onClose: () => void }) {
  const { t } = useTranslation();
  const me = useMe();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const targets = (me.projects ?? []).filter(
    (p) => p.key !== ticket.project && p.role !== 'viewer',
  );
  const [target, setTarget] = useState(targets[0]?.key ?? '');
  const [area, setArea] = useState('');
  const [status, setStatus] = useState('');
  const [children, setChildren] = useState(true);
  const { data: project } = useProject(target);
  const workflow = project?.workflows.find((w) => w.type === ticket.type);
  const sameArea = (project?.areas ?? []).some(
    (a) => a.name.toLowerCase() === (ticket.area ?? '').toLowerCase(),
  );
  const needsArea = Boolean(ticket.area) && !sameArea;
  const sameStatus = workflow?.statuses.some((s) => s.name === ticket.status.name);
  const move = useMutation({
    mutationFn: () =>
      moveTicket(ticket.key, {
        target_project: target,
        area_mapping: needsArea && area ? { [ticket.area!]: area } : {},
        status_mapping: status ? { [ticket.status.name]: status } : {},
        include_children: children,
      }),
    onSuccess: async (moved) => {
      await queryClient.invalidateQueries({ queryKey: ticketKeys.all });
      onClose();
      await navigate({ to: '/t/$key', params: { key: moved.key }, replace: true });
    },
  });
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={t('move.title', { key: ticket.key })}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            disabled={!target || move.isPending || (needsArea && ticket.type !== 'draft' && !area)}
            onClick={() => move.mutate()}
          >
            {t('move.submit')}
          </Button>
        </>
      }
    >
      <FormError>{move.error ? errorMessage(move.error) : null}</FormError>
      {targets.length === 0 ? (
        <S.Help>{t('move.noTargets')}</S.Help>
      ) : (
        <>
          <Field label={t('move.project')}>
            <Select value={target} onChange={(e) => setTarget(e.target.value)}>
              {targets.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.key} · {p.name}
                </option>
              ))}
            </Select>
          </Field>
          {needsArea && (
            <Field label={t('move.areaFor', { area: ticket.area })}>
              <Select value={area} onChange={(e) => setArea(e.target.value)}>
                <option value="">—</option>
                {project?.areas.map((a) => (
                  <option key={a.name} value={a.name}>
                    {a.name}
                  </option>
                ))}
              </Select>
            </Field>
          )}
          <Field
            label={t('move.statusFor', { status: ticket.status.name })}
            hint={sameStatus ? t('move.sameStatus') : t('move.initialStatus')}
          >
            <Select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">{t('move.automatic')}</option>
              {workflow?.statuses.map((s) => (
                <option key={s.name} value={s.name}>
                  {s.name}
                </option>
              ))}
            </Select>
          </Field>
          <S.Checks>
            <label>
              <input
                type="checkbox"
                checked={children}
                onChange={(e) => setChildren(e.target.checked)}
              />
              {t('move.children')}
            </label>
          </S.Checks>
          <S.Help>{t('move.help')}</S.Help>
        </>
      )}
    </Modal>
  );
}
