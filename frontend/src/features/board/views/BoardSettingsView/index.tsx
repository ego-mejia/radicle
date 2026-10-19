import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from '@tanstack/react-router';
import { ArrowLeft } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { Field } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import { SettingsCard } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  boardKeys,
  type BoardPatch,
  deleteBoard,
  fetchBoard,
  patchBoard,
} from '../../../../services/api/boards';
import { CARD_FIELDS, SWIMLANES, type Board } from '../../../../services/api/types';
import { ColumnsEditor } from '../../components/ColumnsEditor';
import { QuickFiltersEditor } from '../../components/QuickFiltersEditor';
import * as S from './style';

type Draft = Required<Omit<BoardPatch, 'kind'>> & { kind: Board['kind'] };

const toDraft = (b: Board): Draft => ({
  name: b.name,
  kind: b.kind,
  source_rql: b.source_rql,
  columns: b.columns,
  wip_mode: b.wip_mode,
  swimlane_by: b.swimlane_by,
  card_fields: b.card_fields,
  done_window_days: b.done_window_days,
});

/** Admin page for one board: scope, columns, WIP, swimlanes, card fields, quick filters. */
export function BoardSettingsView() {
  const { t } = useTranslation();
  const { key, id } = useParams({ from: '/app/p/$key/boards/$id' });
  const projectKey = key.toUpperCase();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const {
    data: board,
    isPending,
    isError,
    refetch,
  } = useQuery({
    queryKey: boardKeys.detail(id),
    queryFn: () => fetchBoard(id),
  });
  const [draft, setDraft] = useState<Draft | null>(null);
  const [confirm, setConfirm] = useState(false);
  useEffect(() => {
    if (board) setDraft(toDraft(board));
  }, [board]);

  const save = useMutation({
    mutationFn: (body: BoardPatch) => patchBoard(id, body),
    onSuccess: () => {
      toast(t('board.saved'));
      void queryClient.invalidateQueries({ queryKey: ['boards'] });
      void queryClient.invalidateQueries({ queryKey: ['tickets', 'board'] });
    },
    onError: (error) => toast(errorMessage(error), 'error'),
  });
  const remove = useMutation({
    mutationFn: () => deleteBoard(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: boardKeys.list(projectKey) });
      void navigate({ to: '/p/$key/board', params: { key: projectKey }, search: {} });
    },
    onError: (error) => toast(errorMessage(error), 'error'),
  });

  if (isPending) return <PageSpinner />;
  if (isError || !board || !draft) return <EmptyState plant="seed" title={t('board.notFound')} />;
  const set = (patch: Partial<Draft>) => setDraft({ ...draft, ...patch });
  const toggleField = (field: string) =>
    set({
      card_fields: draft.card_fields.includes(field)
        ? draft.card_fields.filter((f) => f !== field)
        : [...draft.card_fields, field],
    });

  return (
    <S.Page>
      <S.Header>
        <Link to="/p/$key/board" params={{ key: projectKey }} search={{ board: id }}>
          <ArrowLeft size={14} />
          {t('board.back')}
        </Link>
        <h1>{board.name}</h1>
        <S.Actions>
          <Button variant="danger" onClick={() => setConfirm(true)}>
            {t('board.delete')}
          </Button>
          <Button variant="primary" disabled={save.isPending} onClick={() => save.mutate(draft)}>
            {t('common.save')}
          </Button>
        </S.Actions>
      </S.Header>
      <SettingsCard title={t('board.general')}>
        <S.Grid>
          <Field label={t('board.name')}>
            <Input value={draft.name} onChange={(e) => set({ name: e.target.value })} />
          </Field>
          <Field label={t('board.kind')}>
            <Select
              value={draft.kind}
              onChange={(e) => set({ kind: e.target.value as Draft['kind'] })}
            >
              <option value="kanban">Kanban</option>
              <option value="scrum">Scrum</option>
            </Select>
          </Field>
          <Field label={t('board.source')} hint={t('board.sourceHint')}>
            <Input value={draft.source_rql} onChange={(e) => set({ source_rql: e.target.value })} />
          </Field>
          <Field label={t('board.doneWindow')}>
            <Input
              type="number"
              min={1}
              value={draft.done_window_days}
              onChange={(e) => set({ done_window_days: Number(e.target.value) || 14 })}
            />
          </Field>
          <Field label={t('board.wipMode')}>
            <Select
              value={draft.wip_mode}
              onChange={(e) => set({ wip_mode: e.target.value as Draft['wip_mode'] })}
            >
              <option value="soft">{t('board.wipSoft')}</option>
              <option value="hard">{t('board.wipHard')}</option>
            </Select>
          </Field>
          <Field label={t('board.swimlanes')}>
            <Select
              value={draft.swimlane_by}
              onChange={(e) => set({ swimlane_by: e.target.value as Draft['swimlane_by'] })}
            >
              {SWIMLANES.map((lane) => (
                <option key={lane} value={lane}>
                  {t(`board.lanes.${lane}`)}
                </option>
              ))}
            </Select>
          </Field>
        </S.Grid>
      </SettingsCard>
      <SettingsCard title={t('board.columns')} help={t('board.columnsHelp')}>
        <ColumnsEditor
          columns={draft.columns}
          statuses={board.statuses}
          onChange={(columns) => set({ columns })}
        />
      </SettingsCard>
      <SettingsCard title={t('board.cardFields')}>
        <S.Checks role="group" aria-label={t('board.cardFields')}>
          {CARD_FIELDS.map((field) => (
            <label key={field}>
              <input
                type="checkbox"
                checked={draft.card_fields.includes(field)}
                onChange={() => toggleField(field)}
              />
              {t(`board.fields.${field}`)}
            </label>
          ))}
        </S.Checks>
      </SettingsCard>
      <SettingsCard title={t('board.quickFilters')} help={t('board.quickFiltersHelp')}>
        <QuickFiltersEditor board={board} onSaved={() => void refetch()} />
      </SettingsCard>
      <ConfirmDialog
        open={confirm}
        title={t('board.delete')}
        message={t('board.deleteConfirm', { name: board.name })}
        confirmLabel={t('board.delete')}
        onConfirm={() => remove.mutate()}
        onCancel={() => setConfirm(false)}
      />
    </S.Page>
  );
}
