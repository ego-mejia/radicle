import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Select } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { TICKET_TYPES, type Ticket, type TicketType } from '../../../../services/api/types';
import { useProject } from '../../../projects/hooks/useProject';
import type { TicketActions } from '../../hooks/useTicket';

type Props = { ticket: Ticket; actions: TicketActions; onClose: () => void };

/** Draft to Task and friends; asks for an area when the new type needs one. */
export function ChangeTypeModal({ ticket, actions, onClose }: Props) {
  const { t } = useTranslation();
  const { data: project } = useProject(ticket.project);
  const others = TICKET_TYPES.filter((type) => type !== ticket.type);
  const [type, setType] = useState<TicketType>(others[0]!);
  const [area, setArea] = useState(ticket.area ?? '');
  const needsArea = type !== 'draft' && !ticket.area;

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={t('ticket.changeTypeTitle', { key: ticket.key })}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            disabled={(needsArea && !area) || actions.changeType.isPending}
            onClick={() =>
              actions.changeType.mutate(
                { type, area: area && area !== ticket.area ? area : null },
                { onSuccess: onClose },
              )
            }
          >
            {t('ticket.menu.changeType')}
          </Button>
        </>
      }
    >
      <p>{t('ticket.changeTypeHelp')}</p>
      <Field label={t('ticket.fields.type')}>
        <Select value={type} onChange={(e) => setType(e.target.value as TicketType)}>
          {others.map((option) => (
            <option key={option} value={option}>
              {t(`ticket.types.${option}`)}
            </option>
          ))}
        </Select>
      </Field>
      {type !== 'draft' && (
        <Field label={t('ticket.fields.area')}>
          <Select value={area} onChange={(e) => setArea(e.target.value)} required={needsArea}>
            {!ticket.area && <option value="">—</option>}
            {project?.areas.map((a) => (
              <option key={a.name} value={a.name}>
                {a.name}
              </option>
            ))}
          </Select>
        </Field>
      )}
    </Modal>
  );
}
