import { useTranslation } from 'react-i18next';
import { transitionsBetween } from '../../../../../../lib/workflow';
import type { TransitionConf, WorkflowConf } from '../../../../../../services/api/types';
import * as S from './style';

type Props = {
  workflow: WorkflowConf;
  readOnly: boolean;
  onOpen: (transition: TransitionConf) => void;
  onCreate: (from: string | null, to: string) => void;
};

/** From (rows) by to (columns). A filled cell is a transition; click to edit or add one. */
export function TransitionMatrix({ workflow, readOnly, onOpen, onCreate }: Props) {
  const { t } = useTranslation();
  const rows: { ref: string | null; name: string }[] = [
    ...workflow.statuses.map((s) => ({ ref: s.ref, name: s.name })),
    { ref: null, name: t('settings.anyStatus') },
  ];
  return (
    <S.Scroll>
      <S.Table>
        <thead>
          <tr>
            <th scope="col">{t('workflow.fromTo')}</th>
            {workflow.statuses.map((s) => (
              <th key={s.ref} scope="col">
                {s.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.ref ?? '*'}>
              <th scope="row">{row.name}</th>
              {workflow.statuses.map((col) => {
                if (row.ref === col.ref) return <S.Cell key={col.ref} $disabled />;
                const found = transitionsBetween(workflow, row.ref, col.ref);
                return (
                  <S.Cell key={col.ref}>
                    {found.map((tr) => (
                      <S.On key={tr.ref} type="button" onClick={() => onOpen(tr)}>
                        {tr.name}
                      </S.On>
                    ))}
                    {!found.length && !readOnly && (
                      <S.Off
                        type="button"
                        aria-label={t('workflow.addTransition', { from: row.name, to: col.name })}
                        onClick={() => onCreate(row.ref, col.ref)}
                      >
                        +
                      </S.Off>
                    )}
                  </S.Cell>
                );
              })}
            </tr>
          ))}
        </tbody>
      </S.Table>
    </S.Scroll>
  );
}
