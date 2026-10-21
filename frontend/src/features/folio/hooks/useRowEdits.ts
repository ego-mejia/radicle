import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useErrorMessage } from '../../../hooks/useErrorMessage';
import { useToast } from '../../../hooks/useToast';
import {
  type DbRow,
  addRow,
  dbKeys,
  deleteRow,
  patchRow,
} from '../../../services/api/folioDatabases';

/** Changing, adding and deleting a database's rows; each refreshes its views, and a
 * refused value says why in a toast. */
export function useRowEdits(nodeId: string) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const refresh = () => queryClient.invalidateQueries({ queryKey: dbKeys.database(nodeId) });
  const onError = (e: unknown) => toast(errorMessage(e), 'error');
  const change = useMutation({
    mutationFn: ({ row, key, value }: { row: DbRow; key: string; value: unknown }) =>
      patchRow(row.id, { values: { [key]: value } }),
    onSuccess: refresh,
    onError,
  });
  const add = useMutation({ mutationFn: () => addRow(nodeId, {}), onSuccess: refresh, onError });
  const remove = useMutation({
    mutationFn: (row: DbRow) => deleteRow(row.id),
    onSuccess: refresh,
    onError,
  });
  return {
    change: (row: DbRow, key: string, value: unknown) => change.mutate({ row, key, value }),
    add,
    remove: (row: DbRow) => remove.mutate(row),
  };
}
