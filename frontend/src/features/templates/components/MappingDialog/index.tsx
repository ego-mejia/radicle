import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Select } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import type { Mappings } from '../../../../services/api/templates';
import type { StatusConf, TicketType } from '../../../../services/api/types';
import * as S from './style';

export type Removed = { type: TicketType; status: StatusConf };

type Props = {
  removed: Removed[];
  targets: Partial<Record<TicketType, StatusConf[]>>;
  detail?: string;
  pending?: boolean;
  onConfirm: (mappings: Mappings) => void;
  onClose: () => void;
};

function defaultTarget(status: StatusConf, options: StatusConf[]): string {
  const same = options.find((o) => o.category === status.category);
  return (same ?? options.find((o) => o.is_initial) ?? options[0])?.ref ?? '';
}

/** Ask where the tickets of each removed status go before saving. */
export function MappingDialog({ removed, targets, detail, pending, onConfirm, onClose }: Props) {
  const { t } = useTranslation();
  const [choice, setChoice] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      removed.map((r) => [
        `${r.type}:${r.status.ref}`,
        defaultTarget(r.status, targets[r.type] ?? []),
      ]),
    ),
  );
  const confirm = () => {
    const mappings: Record<string, Record<string, string>> = {};
    for (const r of removed) {
      (mappings[r.type] ??= {})[r.status.ref] = choice[`${r.type}:${r.status.ref}`] ?? '';
    }
    onConfirm(mappings);
  };
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={t('workflow.mappingTitle')}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button variant="primary" disabled={pending} onClick={confirm}>
            {t('workflow.mappingConfirm')}
          </Button>
        </>
      }
    >
      <S.Help>{t('workflow.mappingHelp')}</S.Help>
      {detail && <S.Detail>{detail}</S.Detail>}
      {removed.map((r) => {
        const id = `${r.type}:${r.status.ref}`;
        return (
          <Field
            key={id}
            label={t('workflow.mappingFor', {
              status: r.status.name,
              type: t(`ticket.types.${r.type}`),
            })}
          >
            <Select
              value={choice[id]}
              onChange={(e) => setChoice({ ...choice, [id]: e.target.value })}
            >
              {(targets[r.type] ?? []).map((s) => (
                <option key={s.ref} value={s.ref}>
                  {s.name}
                </option>
              ))}
            </Select>
          </Field>
        );
      })}
    </Modal>
  );
}
