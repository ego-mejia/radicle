import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useErrorMessage } from '../../../hooks/useErrorMessage';
import { useToast } from '../../../hooks/useToast';
import {
  addToSprint,
  completeSprint,
  createSprint,
  deleteSprint,
  removeFromSprint,
  type SprintFields,
  startSprint,
} from '../../../services/api/sprints';
import { ticketKeys } from '../../../services/api/tickets';

/** Sprint mutations; every one refreshes tickets, sprints and the backlog. */
export function useSprintActions(boardId: string) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const done = () => queryClient.invalidateQueries({ queryKey: ticketKeys.all });
  const onError = (error: unknown) => toast(errorMessage(error), 'error');
  return {
    create: useMutation({
      mutationFn: (body: SprintFields) => createSprint(boardId, body),
      onSuccess: done,
      onError,
    }),
    start: useMutation({
      mutationFn: (v: { id: string; body: SprintFields }) => startSprint(v.id, v.body),
      onSuccess: done,
    }),
    complete: useMutation({
      mutationFn: (v: { id: string; body: { move_unfinished_to: string; tag_backlog: boolean } }) =>
        completeSprint(v.id, v.body),
      onSuccess: done,
    }),
    remove: useMutation({ mutationFn: deleteSprint, onSuccess: done, onError }),
    /** Move tickets to a sprint id, or to 'backlog' out of `from`. */
    move: useMutation({
      mutationFn: async (v: { keys: string[]; to: string; from?: Record<string, string> }) => {
        if (v.to !== 'backlog') return addToSprint(v.to, v.keys);
        const bySprint = new Map<string, string[]>();
        for (const key of v.keys) {
          const sprint = v.from?.[key];
          if (sprint && sprint !== 'backlog')
            bySprint.set(sprint, [...(bySprint.get(sprint) ?? []), key]);
        }
        for (const [sprint, keys] of bySprint) await removeFromSprint(sprint, keys);
        return { keys: v.keys };
      },
      onSuccess: done,
      onError,
    }),
  };
}
