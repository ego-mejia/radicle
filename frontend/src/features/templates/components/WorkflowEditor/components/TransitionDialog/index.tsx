import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../components/ui/Button';
import { Field } from '../../../../../../components/ui/Field';
import { Input } from '../../../../../../components/ui/Input';
import { Modal } from '../../../../../../components/ui/Modal';
import {
  RESOLUTIONS,
  type Resolution,
  type TransitionConf,
  type WorkflowConf,
} from '../../../../../../services/api/types';
import * as S from './style';

type Props = {
  workflow: WorkflowConf;
  transition: TransitionConf;
  readOnly: boolean;
  onSave: (transition: TransitionConf) => void;
  onDelete: () => void;
  onClose: () => void;
  /** Extra editors for the transition, e.g. its rules. */
  children?: (draft: TransitionConf, set: (next: TransitionConf) => void) => React.ReactNode;
};

/** Name a transition and, when it goes to a done status, pick the allowed resolutions. */
export function TransitionDialog({
  workflow,
  transition,
  readOnly,
  onSave,
  onDelete,
  onClose,
  children,
}: Props) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState<TransitionConf>(transition);
  const target = workflow.statuses.find((s) => s.ref === draft.to);
  const from = workflow.statuses.find((s) => s.ref === draft.from);
  const toDone = target?.category === 'done';
  const allowed = draft.allowed_resolutions ?? null;
  const toggle = (r: Resolution) => {
    const current = allowed ?? [...RESOLUTIONS];
    const next = current.includes(r) ? current.filter((x) => x !== r) : [...current, r];
    setDraft({
      ...draft,
      allowed_resolutions: next.length === RESOLUTIONS.length ? null : next,
    });
  };

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={`${from?.name ?? t('settings.anyStatus')} → ${target?.name ?? draft.to}`}
      width={560}
      footer={
        readOnly ? (
          <Button onClick={onClose}>{t('common.close')}</Button>
        ) : (
          <>
            <S.Danger variant="ghost" onClick={onDelete}>
              {t('workflow.deleteTransition')}
            </S.Danger>
            <Button onClick={onClose}>{t('common.cancel')}</Button>
            <Button
              variant="primary"
              disabled={!draft.name.trim() || (toDone && allowed?.length === 0)}
              onClick={() => onSave({ ...draft, name: draft.name.trim() })}
            >
              {t('common.save')}
            </Button>
          </>
        )
      }
    >
      <Field label={t('workflow.transitionName')}>
        <Input
          value={draft.name}
          autoFocus
          disabled={readOnly}
          onChange={(e) => setDraft({ ...draft, name: e.target.value })}
        />
      </Field>
      {toDone && (
        <Field label={t('workflow.resolutions')} hint={t('workflow.resolutionsHint')} group>
          <S.Checks>
            {RESOLUTIONS.map((r) => (
              <label key={r}>
                <input
                  type="checkbox"
                  disabled={readOnly}
                  checked={allowed === null || allowed.includes(r)}
                  onChange={() => toggle(r)}
                />
                {t(`ticket.resolutions.${r}`)}
              </label>
            ))}
          </S.Checks>
        </Field>
      )}
      {children?.(draft, setDraft)}
    </Modal>
  );
}
