import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useErrorMessage } from '../../../hooks/useErrorMessage';
import { useToast } from '../../../hooks/useToast';
import { authKeys } from '../../../services/api/auth';
import { projectKeys } from '../../../services/api/projects';

/** A settings mutation that refreshes the project and reports errors as toasts. */
export function useSettingsMutation<V, R>(
  project: string,
  fn: (vars: V) => Promise<R>,
  onDone?: () => void,
) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  return useMutation({
    mutationFn: fn,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: projectKeys.all });
      await queryClient.invalidateQueries({ queryKey: projectKeys.detail(project) });
      await queryClient.invalidateQueries({ queryKey: authKeys.me });
      onDone?.();
    },
    onError: (error) => toast(errorMessage(error), 'error'),
  });
}
