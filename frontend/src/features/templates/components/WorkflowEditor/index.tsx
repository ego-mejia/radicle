import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { freshRef, unreachable, workflowErrors } from '../../../../lib/workflow';
import type { TransitionConf, WorkflowConf } from '../../../../services/api/types';
import { RulesEditor } from '../RulesEditor';
import { StatusList } from './components/StatusList';
import { TransitionDialog } from './components/TransitionDialog';
import { TransitionMatrix } from './components/TransitionMatrix';
import { WorkflowDiagram } from './components/WorkflowDiagram';
import * as S from './style';

type Props = {
  value: WorkflowConf;
  onChange: (next: WorkflowConf) => void;
  readOnly?: boolean;
  /** Custom field keys offered to field rules. */
  customFields?: string[];
};

/** Statuses, transition matrix and a live diagram for one ticket type. */
export function WorkflowEditor({ value, onChange, readOnly = false, customFields = [] }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState<TransitionConf | null>(null);
  const transitions = value.transitions ?? [];
  const errors = workflowErrors(value);
  const lost = unreachable(value);

  const create = (from: string | null, to: string) => {
    const target = value.statuses.find((s) => s.ref === to);
    const name = target?.name ?? to;
    const draft: TransitionConf = {
      ref: freshRef(
        name,
        transitions.map((tr) => tr.ref),
      ),
      name,
      from,
      to,
      allowed_resolutions: null,
      rules: [],
    };
    setOpen(draft);
  };

  const save = (next: TransitionConf) => {
    const exists = transitions.some((tr) => tr.ref === next.ref);
    onChange({
      ...value,
      transitions: exists
        ? transitions.map((tr) => (tr.ref === next.ref ? next : tr))
        : [...transitions, next],
    });
    setOpen(null);
  };

  return (
    <S.Grid>
      <S.Column>
        <S.Heading>{t('workflow.statuses')}</S.Heading>
        <StatusList
          statuses={value.statuses}
          readOnly={readOnly}
          onChange={(statuses, removedRef) =>
            onChange({
              ...value,
              statuses,
              transitions: removedRef
                ? transitions.filter((tr) => tr.from !== removedRef && tr.to !== removedRef)
                : transitions,
            })
          }
        />
        <S.Heading>{t('workflow.transitions')}</S.Heading>
        <TransitionMatrix workflow={value} readOnly={readOnly} onOpen={setOpen} onCreate={create} />
        {errors.map((e) => (
          <S.Error key={e.key} role="alert">
            {t(e.key, e.params)}
          </S.Error>
        ))}
        {lost.length > 0 && (
          <S.Warning>{t('workflow.unreachable', { names: lost.join(', ') })}</S.Warning>
        )}
      </S.Column>
      <S.Column>
        <S.Heading>{t('workflow.preview')}</S.Heading>
        <WorkflowDiagram workflow={value} />
      </S.Column>
      {open && (
        <TransitionDialog
          workflow={value}
          transition={open}
          readOnly={readOnly}
          onSave={save}
          onClose={() => setOpen(null)}
          onDelete={() => {
            onChange({ ...value, transitions: transitions.filter((tr) => tr.ref !== open.ref) });
            setOpen(null);
          }}
        >
          {(draft, set) => (
            <RulesEditor
              rules={draft.rules ?? []}
              readOnly={readOnly}
              customFields={customFields}
              onChange={(rules) => set({ ...draft, rules })}
            />
          )}
        </TransitionDialog>
      )}
    </S.Grid>
  );
}
