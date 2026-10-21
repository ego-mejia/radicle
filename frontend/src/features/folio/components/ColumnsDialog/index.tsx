import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../components/ui/Button';
import { FormError } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  COLUMN_TYPES,
  type ColumnType,
  type DbColumn,
  type FolioDatabase,
  dbKeys,
  patchDatabase,
} from '../../../../services/api/folioDatabases';
import { ChoicesEditor } from './components/ChoicesEditor';
import { withKeys } from './keys';
import * as S from './style';

type Props = { database: FolioDatabase; onClose: () => void };

const HAS_CHOICES: ColumnType[] = ['select', 'multi_select'];

/** Add, rename, retype and remove a database's columns, and edit a select's choices. A
 * new column shows in every view; a new type keeps the values that fit it. */
export function ColumnsDialog({ database, onClose }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [columns, setColumns] = useState<DbColumn[]>(database.columns);
  const was = new Map(database.columns.map((c) => [c.key, c.type]));
  const change = (i: number, patch: Partial<DbColumn>) =>
    setColumns((cs) => cs.map((c, j) => (j === i ? { ...c, ...patch } : c)));
  const save = useMutation({
    mutationFn: () => {
      const next = withKeys(columns);
      const added = next.filter((c) => !was.has(c.key)).map((c) => c.key);
      const views = database.views.map((v) => ({
        ...v,
        visible_columns: [...v.visible_columns, ...added],
      }));
      return patchDatabase(database.node_id, { columns: next, views });
    },
    onSuccess: async (saved) => {
      await queryClient.invalidateQueries({ queryKey: dbKeys.database(database.node_id) });
      if (saved.cleared) toast(t('folio.db.cleared', { count: saved.cleared }), 'warning');
      onClose();
    },
  });

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={t('folio.db.columns')}
      width={680}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            onClick={() => save.mutate()}
            disabled={save.isPending || columns.some((c) => !c.name.trim())}
          >
            {t('common.save')}
          </Button>
        </>
      }
    >
      <S.List>
        {columns.map((c, i) => (
          <li key={c.key || `new-${i}`}>
            <S.Line>
              <Input
                aria-label={t('folio.db.columnName')}
                value={c.name}
                maxLength={100}
                onChange={(e) => change(i, { name: e.target.value })}
              />
              <Select
                aria-label={t('folio.db.columnType')}
                value={c.type}
                onChange={(e) => {
                  const type = e.target.value as ColumnType;
                  change(i, { type, options: HAS_CHOICES.includes(type) ? c.options : {} });
                }}
              >
                {COLUMN_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {t(`folio.db.type.${type}`)}
                  </option>
                ))}
              </Select>
              <IconButton
                label={t('folio.db.removeColumn', { column: c.name })}
                disabled={columns.length === 1}
                onClick={() => setColumns((cs) => cs.filter((_, j) => j !== i))}
              >
                <X />
              </IconButton>
            </S.Line>
            {was.has(c.key) && was.get(c.key) !== c.type && (
              <S.Note role="note">{t('folio.db.typeChange')}</S.Note>
            )}
            {HAS_CHOICES.includes(c.type) && (
              <ChoicesEditor
                choices={c.options.choices ?? []}
                onChange={(choices) => change(i, { options: { choices } })}
              />
            )}
          </li>
        ))}
      </S.List>
      <Button
        size="sm"
        variant="ghost"
        onClick={() =>
          setColumns((cs) => [
            ...cs,
            {
              key: '',
              name: t('folio.db.newColumnName', { n: cs.length + 1 }),
              type: 'text',
              options: {},
            },
          ])
        }
      >
        <Plus aria-hidden />
        {t('folio.db.addColumn')}
      </Button>
      {save.error && <FormError>{errorMessage(save.error)}</FormError>}
    </Modal>
  );
}
