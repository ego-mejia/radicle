import { useTranslation } from 'react-i18next';
import { Field } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import type { Board, ProjectDetail, ReportType, Sprint } from '../../../../services/api/types';
import * as S from './style';

export type Filters = {
  board?: string;
  sprint?: string;
  milestone?: string;
  area?: string;
  from?: string;
  to?: string;
  field?: string;
  interval?: string;
  by?: string;
};

type Props = {
  type: ReportType;
  project: ProjectDetail;
  boards: Board[];
  sprints: Sprint[];
  value: Filters;
  onChange: (next: Filters) => void;
};

const SPRINT_REPORTS: ReportType[] = ['burndown', 'sprint'];
const RANGE_REPORTS: ReportType[] = ['cfd', 'control_chart', 'created_resolved', 'burnup'];
const SCOPE_REPORTS: ReportType[] = [
  'cfd',
  'control_chart',
  'created_resolved',
  'distribution',
  'time',
];
const FIELDS = ['area', 'priority', 'assignee', 'type', 'status', 'tag', 'milestone'];

/** The filters each report understands: sprint, board, milestone, area, range... */
export function ReportFilters({ type, project, boards, sprints, value, onChange }: Props) {
  const { t } = useTranslation();
  const set = (patch: Filters) => onChange({ ...value, ...patch });
  const scrum = boards.filter((b) => b.kind === 'scrum');
  const needsSprint = SPRINT_REPORTS.includes(type) || (type === 'burnup' && !value.milestone);
  const boardChoices = type === 'velocity' || needsSprint ? scrum : boards;
  const showBoard = type === 'velocity' || needsSprint || SCOPE_REPORTS.includes(type);
  const showMilestone = type === 'milestone_progress' || type === 'burnup';
  return (
    <S.Bar>
      {showBoard && (
        <Field label={t('reports.board')}>
          <Select
            value={value.board ?? ''}
            onChange={(e) => set({ board: e.target.value || undefined, sprint: undefined })}
          >
            {SCOPE_REPORTS.includes(type) && <option value="">{t('reports.wholeProject')}</option>}
            {boardChoices.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
        </Field>
      )}
      {needsSprint && (
        <Field label={t('reports.sprint')}>
          <Select
            value={value.sprint ?? ''}
            onChange={(e) => set({ sprint: e.target.value || undefined })}
          >
            {sprints.length === 0 && <option value="">{t('reports.noSprints')}</option>}
            {sprints
              .filter((s) => s.state !== 'future')
              .map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} · {t(`sprints.states.${s.state}`)}
                </option>
              ))}
          </Select>
        </Field>
      )}
      {showMilestone && (
        <Field label={t('reports.milestone')}>
          <Select
            value={value.milestone ?? ''}
            onChange={(e) => set({ milestone: e.target.value || undefined })}
          >
            {type === 'burnup' && <option value="">{t('reports.useSprint')}</option>}
            {project.milestones.map((m) => (
              <option key={m.name} value={m.name}>
                {m.name}
              </option>
            ))}
          </Select>
        </Field>
      )}
      {SCOPE_REPORTS.includes(type) && (
        <Field label={t('reports.area')}>
          <Select
            value={value.area ?? ''}
            onChange={(e) => set({ area: e.target.value || undefined })}
          >
            <option value="">{t('board.allAreas')}</option>
            {project.areas.map((a) => (
              <option key={a.name} value={a.name}>
                {a.name}
              </option>
            ))}
          </Select>
        </Field>
      )}
      {RANGE_REPORTS.includes(type) && (
        <>
          <Field label={t('reports.from')}>
            <Input
              type="date"
              value={value.from ?? ''}
              onChange={(e) => set({ from: e.target.value || undefined })}
            />
          </Field>
          <Field label={t('reports.to')}>
            <Input
              type="date"
              value={value.to ?? ''}
              onChange={(e) => set({ to: e.target.value || undefined })}
            />
          </Field>
        </>
      )}
      {type === 'distribution' && (
        <Field label={t('reports.field')}>
          <Select value={value.field ?? 'area'} onChange={(e) => set({ field: e.target.value })}>
            {FIELDS.map((f) => (
              <option key={f} value={f}>
                {t(`reports.fields.${f}`)}
              </option>
            ))}
          </Select>
        </Field>
      )}
      {type === 'created_resolved' && (
        <Field label={t('reports.interval')}>
          <Select
            value={value.interval ?? 'day'}
            onChange={(e) => set({ interval: e.target.value })}
          >
            <option value="day">{t('reports.day')}</option>
            <option value="week">{t('reports.week')}</option>
          </Select>
        </Field>
      )}
      {type === 'time' && (
        <Field label={t('reports.groupBy')}>
          <Select value={value.by ?? 'ticket'} onChange={(e) => set({ by: e.target.value })}>
            {['ticket', 'milestone', 'area', 'assignee'].map((b) => (
              <option key={b} value={b}>
                {t(`reports.by.${b}`)}
              </option>
            ))}
          </Select>
        </Field>
      )}
    </S.Bar>
  );
}
