import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field, FormError } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import {
  type DbView,
  type FolioDatabase,
  type ViewKind,
  dbKeys,
  patchDatabase,
} from '../../../../services/api/folioDatabases';
import { ViewRules } from './components/ViewRules';
import * as S from './style';

type Props = {
  database: FolioDatabase;
  /** The view to change; null makes a new one. */
  view: DbView | null;
  onClose: (saved?: string) => void;
};

const KINDS: ViewKind[] = ['table', 'cards', 'board'];

/** A view's name, kind, filters, sort and columns. Saving replaces the database's views. */
export function ViewSettings({ database, view, onClose }: Props) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const columns = database.columns;
  const selects = columns.filter((c) => c.type === 'select');
  const [draft, setDraft] = useState<DbView>(
    view ?? {
      id: '',
      name: t('folio.db.newViewName', { n: database.views.length + 1 }),
      kind: 'table',
      group_by: null,
      filters: [],
      sort: [],
      visible_columns: columns.map((c) => c.key),
    },
  );
  const set = (patch: Partial<DbView>) => setDraft((d) => ({ ...d, ...patch }));
  const save = useMutation({
    mutationFn: (views: DbView[]) => patchDatabase(database.node_id, { views }),
    onSuccess: async (saved) => {
      await queryClient.invalidateQueries({ queryKey: dbKeys.database(database.node_id) });
      // Open the view just saved; after deleting one, the first.
      const kept = saved.views.find((v) => v.id === view?.id);
      onClose(kept?.id ?? saved.views[view ? 0 : saved.views.length - 1]?.id);
    },
  });
  const others = database.views.filter((v) => v.id !== view?.id);
  const submit = () => {
    const { id, ...rest } = draft;
    save.mutate(
      view ? database.views.map((v) => (v.id === id ? draft : v)) : [...others, rest as DbView],
    );
  };

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={view ? t('folio.db.editView') : t('folio.db.newView')}
      width={640}
      footer={
        <>
          {view && others.length > 0 && (
            <S.Danger>
              <Button variant="danger" onClick={() => save.mutate(others)}>
                {t('folio.db.deleteView')}
              </Button>
            </S.Danger>
          )}
          <Button onClick={() => onClose()}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            onClick={submit}
            disabled={save.isPending || !draft.name.trim()}
          >
            {t('common.save')}
          </Button>
        </>
      }
    >
      <S.Form>
        <S.Row>
          <Field label={t('folio.db.viewName')}>
            <Input
              value={draft.name}
              maxLength={100}
              onChange={(e) => set({ name: e.target.value })}
            />
          </Field>
          <Field label={t('folio.db.viewKind')}>
            <Select
              value={draft.kind}
              onChange={(e) => {
                const kind = e.target.value as ViewKind;
                set({
                  kind,
                  group_by: kind === 'board' ? (draft.group_by ?? selects[0]?.key ?? null) : null,
                });
              }}
            >
              {KINDS.map((k) => (
                <option key={k} value={k} disabled={k === 'board' && selects.length === 0}>
                  {t(`folio.db.kind.${k}`)}
                </option>
              ))}
            </Select>
          </Field>
          {draft.kind === 'board' && (
            <Field label={t('folio.db.groupBy')}>
              <Select
                value={draft.group_by ?? ''}
                onChange={(e) => set({ group_by: e.target.value })}
              >
                {selects.map((c) => (
                  <option key={c.key} value={c.key}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </Field>
          )}
        </S.Row>

        <ViewRules columns={columns} draft={draft} set={set} />

        <S.Section>
          <h3>{t('folio.db.shownColumns')}</h3>
          <S.Checks>
            {columns.map((c) => (
              <label key={c.key}>
                <input
                  type="checkbox"
                  checked={draft.visible_columns.includes(c.key)}
                  onChange={(e) =>
                    set({
                      visible_columns: e.target.checked
                        ? columns
                            .map((x) => x.key)
                            .filter((k) => k === c.key || draft.visible_columns.includes(k))
                        : draft.visible_columns.filter((k) => k !== c.key),
                    })
                  }
                />
                {c.name}
              </label>
            ))}
          </S.Checks>
        </S.Section>
        {save.error && <FormError>{errorMessage(save.error)}</FormError>}
      </S.Form>
    </Modal>
  );
}
