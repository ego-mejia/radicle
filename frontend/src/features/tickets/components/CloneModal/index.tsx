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
import { cloneTicket } from '../../../../services/api/bulk';
import { ticketKeys } from '../../../../services/api/tickets';
import type { Ticket } from '../../../../services/api/types';
import { useProject } from '../../../projects/hooks/useProject';
import * as S from '../MoveModal/style';

const INCLUDES = [
  'description',
  'checklist_state',
  'tags',
  'custom_fields',
  'collaborators',
  'attachments',
  'children',
] as const;

/** Clone with options; another project may need an area mapping. */
export function CloneModal({ ticket, onClose }: { ticket: Ticket; onClose: () => void }) {
  const { t } = useTranslation();
  const me = useMe();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [target, setTarget] = useState(ticket.project);
  const [include, setInclude] = useState<string[]>(['description', 'tags', 'custom_fields']);
  const [area, setArea] = useState('');
  const { data: targetProject } = useProject(target);
  const needsArea =
    target !== ticket.project &&
    ticket.area !== null &&
    !(targetProject?.areas ?? []).some((a) => a.name.toLowerCase() === ticket.area!.toLowerCase());
  const clone = useMutation({
    mutationFn: () =>
      cloneTicket(ticket.key, {
        target_project: target,
        include,
        area_mapping: needsArea && area ? { [ticket.area!]: area } : {},
      }),
    onSuccess: async (copy) => {
      await queryClient.invalidateQueries({ queryKey: ticketKeys.all });
      onClose();
      await navigate({ to: '/t/$key', params: { key: copy.key } });
    },
  });
  const writable = (me.projects ?? []).filter((p) => p.permissions.includes('ticket.create'));
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={t('clone.title', { key: ticket.key })}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            disabled={clone.isPending || (needsArea && !area)}
            onClick={() => clone.mutate()}
          >
            {t('clone.submit')}
          </Button>
        </>
      }
    >
      <FormError>{clone.error ? errorMessage(clone.error) : null}</FormError>
      <Field label={t('clone.project')}>
        <Select value={target} onChange={(e) => setTarget(e.target.value)}>
          {writable.map((p) => (
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
            {targetProject?.areas.map((a) => (
              <option key={a.name} value={a.name}>
                {a.name}
              </option>
            ))}
          </Select>
        </Field>
      )}
      <Field label={t('clone.include')} group>
        <S.Checks>
          {INCLUDES.map((value) => (
            <label key={value}>
              <input
                type="checkbox"
                checked={include.includes(value)}
                onChange={() =>
                  setInclude((prev) =>
                    prev.includes(value) ? prev.filter((x) => x !== value) : [...prev, value],
                  )
                }
              />
              {t(`clone.includes.${value}`)}
            </label>
          ))}
        </S.Checks>
      </Field>
      <S.Help>{t('clone.help')}</S.Help>
    </Modal>
  );
}
