import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useErrorMessage } from '../../../hooks/useErrorMessage';
import { useToast } from '../../../hooks/useToast';
import {
  addComment,
  commentKeys,
  deleteComment,
  editComment,
  fetchPeople,
  fetchThreads,
  type FolioCommentIn,
  setResolved,
} from '../../../services/api/folioComments';

/** A page's comment threads (resolved ones too, filtered by the panel) and what you can do
 * with them. Every change refetches the threads. */
export function useComments(nodeId: string) {
  const client = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const threads = useQuery({
    queryKey: commentKeys.threads(nodeId, true),
    queryFn: () => fetchThreads(nodeId, true),
  });
  const people = useQuery({
    queryKey: commentKeys.people(''),
    queryFn: () => fetchPeople(''),
    staleTime: 5 * 60_000,
  });
  const done = {
    onSuccess: () => client.invalidateQueries({ queryKey: commentKeys.all(nodeId) }),
    onError: (e: unknown) => toast(errorMessage(e), 'error'),
  };
  const add = useMutation({
    mutationFn: (body: FolioCommentIn) => addComment(nodeId, body),
    ...done,
  });
  const edit = useMutation({
    mutationFn: ({ id, body }: { id: string; body: string }) => editComment(id, body),
    ...done,
  });
  const remove = useMutation({ mutationFn: deleteComment, ...done });
  const resolve = useMutation({
    mutationFn: ({ id, resolved }: { id: string; resolved: boolean }) => setResolved(id, resolved),
    ...done,
  });
  const mentions = (people.data ?? []).map((p) => ({ handle: p.handle, name: p.name }));
  return { threads, mentions, add, edit, remove, resolve };
}
