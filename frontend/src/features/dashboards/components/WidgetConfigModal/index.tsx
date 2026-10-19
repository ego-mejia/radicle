import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Select, Textarea } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useMe } from '../../../../hooks/useMe';
import { boardKeys, fetchBoards } from '../../../../services/api/boards';
import { fetchFilters, workKeys } from '../../../../services/api/work';
import type { WidgetType } from '../../../../services/api/types';
import * as S from './style';

type Config = Record<string, unknown>;

type Props = {
  type: WidgetType;
  title?: string;
  config?: Config;
  error?: string | null;
  pending?: boolean;
  onCancel: () => void;
  onSave: (title: string, config: Config) => void;
};

const FIELDS = ['area', 'priority', 'assignee', 'type', 'status', 'tag', 'milestone'];
const RQL_TYPES: WidgetType[] = ['count', 'distribution', 'created_vs_resolved', 'blocked_tickets'];

/** Title and the settings each widget type needs. */
export function WidgetConfigModal({
  type,
  title,
  config = {},
  error,
  pending,
  onCancel,
  onSave,
}: Props) {
  const { t } = useTranslation();
  const me = useMe();
  const [name, setName] = useState(title ?? t(`dashboards.widgets.${type}.name`));
  const [values, setValues] = useState<Config>(config);
  const set = (patch: Config) => setValues((v) => ({ ...v, ...patch }));
  const str = (key: string) => (values[key] == null ? '' : String(values[key]));
  const project = str('project') || me.projects?.[0]?.key || '';
  const { data: savedFilters = [] } = useQuery({
    queryKey: workKeys.filters(),
    queryFn: () => fetchFilters(),
    enabled: type === 'filter_results',
  });
  const needsBoard = type === 'sprint_burndown' || type === 'cumulative_flow';
  const { data: boards = [] } = useQuery({
    queryKey: boardKeys.list(project),
    queryFn: () => fetchBoards(project),
    enabled: needsBoard && Boolean(project),
  });
  const choices = type === 'sprint_burndown' ? boards.filter((b) => b.kind === 'scrum') : boards;

  const submit = () => {
    const out: Config = { ...values };
    if (needsBoard && !out.board && choices[0]) out.board = choices[0].id;
    if (type === 'milestone_progress' && !out.project) out.project = project;
    if (type === 'distribution' && !out.field) out.field = 'area';
    onSave(name, out);
  };

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onCancel()}
      title={t(`dashboards.widgets.${type}.name`)}
      footer={
        <>
          <Button onClick={onCancel}>{t('common.cancel')}</Button>
          <Button variant="primary" disabled={pending || !name.trim()} onClick={submit}>
            {t('common.save')}
          </Button>
        </>
      }
    >
      <S.Form>
        <Field label={t('dashboards.widgetTitle')}>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        {type === 'filter_results' && (
          <Field label={t('dashboards.savedFilter')} hint={t('dashboards.orRql')}>
            <Select
              value={str('filter')}
              onChange={(e) => set({ filter: e.target.value || undefined })}
            >
              <option value="">—</option>
              {savedFilters.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </Select>
          </Field>
        )}
        {(RQL_TYPES.includes(type) || (type === 'filter_results' && !values.filter)) && (
          <Field
            label="RQL"
            hint={type === 'blocked_tickets' ? t('dashboards.rqlOptional') : undefined}
          >
            <Input
              value={str('rql')}
              placeholder="project = PA AND type = bug"
              onChange={(e) => set({ rql: e.target.value })}
            />
          </Field>
        )}
        {type === 'count' && (
          <Field label={t('dashboards.label')}>
            <Input value={str('label')} onChange={(e) => set({ label: e.target.value })} />
          </Field>
        )}
        {type === 'filter_results' && (
          <Field label={t('dashboards.limit')}>
            <Input
              type="number"
              min={1}
              max={50}
              value={str('limit') || '10'}
              onChange={(e) => set({ limit: Number(e.target.value) })}
            />
          </Field>
        )}
        {type === 'distribution' && (
          <S.Row>
            <Field label={t('reports.field')}>
              <Select
                value={str('field') || 'area'}
                onChange={(e) => set({ field: e.target.value })}
              >
                {FIELDS.map((f) => (
                  <option key={f} value={f}>
                    {t(`reports.fields.${f}`)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label={t('dashboards.chart')}>
              <Select
                value={str('chart') || 'bar'}
                onChange={(e) => set({ chart: e.target.value })}
              >
                <option value="bar">{t('dashboards.bars')}</option>
                <option value="pie">{t('dashboards.pie')}</option>
              </Select>
            </Field>
          </S.Row>
        )}
        {(type === 'milestone_progress' || needsBoard) && (
          <Field label={t('dashboards.project')}>
            <Select
              value={project}
              onChange={(e) => set({ project: e.target.value, board: undefined })}
            >
              {(me.projects ?? []).map((p) => (
                <option key={p.key} value={p.key}>
                  {p.key} · {p.name}
                </option>
              ))}
            </Select>
          </Field>
        )}
        {type === 'milestone_progress' && (
          <Field label={t('reports.milestone')}>
            <Input
              value={str('milestone')}
              placeholder="V1"
              onChange={(e) => set({ milestone: e.target.value })}
            />
          </Field>
        )}
        {needsBoard && (
          <Field label={t('reports.board')}>
            <Select
              value={str('board') || choices[0]?.id || ''}
              onChange={(e) => set({ board: e.target.value })}
            >
              {choices.length === 0 && <option value="">{t('reports.needScrum')}</option>}
              {choices.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </Select>
          </Field>
        )}
        {(type === 'created_vs_resolved' || type === 'cumulative_flow') && (
          <Field label={t('dashboards.days')}>
            <Input
              type="number"
              min={7}
              max={365}
              value={str('days') || '30'}
              onChange={(e) => set({ days: Number(e.target.value) })}
            />
          </Field>
        )}
        {type === 'markdown' && (
          <Field label={t('dashboards.text')}>
            <Textarea
              rows={6}
              value={str('text')}
              onChange={(e) => set({ text: e.target.value })}
            />
          </Field>
        )}
        <FormError>{error}</FormError>
      </S.Form>
    </Modal>
  );
}
