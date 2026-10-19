import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../components/ui/Button';
import { Input } from '../../../../components/ui/Input';
import { SettingsParts as P } from '../../../../components/ui/SettingsCard';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { deleteQuickFilter, saveQuickFilter } from '../../../../services/api/boards';
import type { Board } from '../../../../services/api/types';

/** Named RQL toggles shown above the board. */
export function QuickFiltersEditor({ board, onSaved }: { board: Board; onSaved: () => void }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [rql, setRql] = useState('');
  const done = () => {
    onSaved();
    void queryClient.invalidateQueries({ queryKey: ['boards'] });
    void queryClient.invalidateQueries({ queryKey: ['tickets', 'board'] });
  };
  const onError = (error: unknown) => toast(errorMessage(error), 'error');
  const save = useMutation({
    mutationFn: (v: { id?: string; name: string; rql: string }) =>
      saveQuickFilter(board.id, { name: v.name, rql: v.rql }, v.id),
    onSuccess: done,
    onError,
  });
  const remove = useMutation({
    mutationFn: (id: string) => deleteQuickFilter(board.id, id),
    onSuccess: done,
    onError,
  });
  return (
    <P.Rows>
      {board.quick_filters.map((q) => (
        <P.Row key={q.id}>
          <Input
            aria-label={t('board.filterName')}
            defaultValue={q.name}
            onBlur={(e) =>
              e.target.value.trim() &&
              e.target.value !== q.name &&
              save.mutate({ id: q.id, name: e.target.value.trim(), rql: q.rql })
            }
          />
          <P.Grow>
            <Input
              aria-label={t('board.filterRql')}
              defaultValue={q.rql}
              onBlur={(e) =>
                e.target.value.trim() &&
                e.target.value !== q.rql &&
                save.mutate({ id: q.id, name: q.name, rql: e.target.value.trim() })
              }
            />
          </P.Grow>
          <IconButton
            label={t('board.removeFilter', { name: q.name })}
            onClick={() => remove.mutate(q.id)}
          >
            <Trash2 />
          </IconButton>
        </P.Row>
      ))}
      <P.Inline
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim() || !rql.trim()) return;
          save.mutate(
            { name: name.trim(), rql: rql.trim() },
            {
              onSuccess: () => {
                setName('');
                setRql('');
              },
            },
          );
        }}
      >
        <Input
          aria-label={t('board.filterName')}
          placeholder={t('board.filterName')}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Input
          aria-label={t('board.filterRql')}
          placeholder="assignee = currentUser()"
          value={rql}
          onChange={(e) => setRql(e.target.value)}
        />
        <Button type="submit" size="sm">
          {t('board.addFilter')}
        </Button>
      </P.Inline>
    </P.Rows>
  );
}
