import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useErrorMessage } from '../../../hooks/useErrorMessage';
import { useToast } from '../../../hooks/useToast';
import { isApiError } from '../../../services/api/client';
import { projectKeys } from '../../../services/api/projects';
import * as api from '../../../services/api/tickets';
import type { Resolution, Ticket, TicketPatch, TicketType } from '../../../services/api/types';

export function useTicket(key: string) {
  return useQuery({ queryKey: api.ticketKeys.detail(key), queryFn: () => api.fetchTicket(key) });
}

type Patch = Omit<TicketPatch, 'expected_version'>;

/**
 * Every mutation of one ticket. Successful responses replace the cached ticket and
 * refresh lists; a 409 version conflict is surfaced instead of overwriting.
 */
export function useTicketActions(ticket: Ticket | undefined) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [conflict, setConflict] = useState(false);
  const key = ticket?.key ?? '';

  const settle = (updated: Ticket) => {
    queryClient.setQueryData(api.ticketKeys.detail(updated.key), updated);
    void queryClient.invalidateQueries({ queryKey: api.ticketKeys.all, refetchType: 'active' });
    void queryClient.invalidateQueries({ queryKey: projectKeys.detail(updated.project) });
    for (const warning of updated.warnings ?? []) {
      toast(
        warning.code === 'blocked'
          ? t('ticket.warningBlocked', { keys: (warning.by ?? []).join(', ') })
          : warning.message,
        'warning',
      );
    }
  };
  const onError = (error: unknown) => {
    if (isApiError(error, 409) && error.problem.current_version !== undefined) {
      setConflict(true);
      return;
    }
    toast(errorMessage(error), 'error');
  };
  const options = { onSuccess: settle, onError };

  const patch = useMutation({
    mutationFn: (body: Patch) => api.patchTicket(key, ticket!.version, body),
    ...options,
  });
  const transition = useMutation({
    mutationFn: (v: { to: string; resolution?: Resolution | null; transition?: string }) =>
      api.transitionTicket(key, v.to, v.resolution, v.transition),
    ...options,
  });
  const changeType = useMutation({
    mutationFn: (v: { type: TicketType; area?: string | null }) =>
      api.changeType(key, v.type, v.area),
    ...options,
  });
  const toggleItem = useMutation({
    mutationFn: (v: { index: number; checked: boolean }) =>
      api.setChecklistItem(key, v.index, v.checked),
    ...options,
  });
  const addCollaborator = useMutation({
    mutationFn: (handle: string) => api.addCollaborator(key, handle),
    ...options,
  });
  const removeCollaborator = useMutation({
    mutationFn: (handle: string) => api.removeCollaborator(key, handle),
    ...options,
  });
  const refresh = () => queryClient.invalidateQueries({ queryKey: api.ticketKeys.detail(key) });
  const addLink = useMutation({
    mutationFn: (v: { type: string; target: string }) => api.addLink(key, v.type, v.target),
    onSuccess: () => void refresh(),
    onError,
  });
  const removeLink = useMutation({
    mutationFn: (id: string) => api.removeLink(id),
    onSuccess: () => void refresh(),
    onError,
  });

  const reload = async () => {
    await queryClient.refetchQueries({ queryKey: api.ticketKeys.detail(key) });
    setConflict(false);
  };

  return {
    patch,
    transition,
    changeType,
    toggleItem,
    addCollaborator,
    removeCollaborator,
    addLink,
    removeLink,
    conflict,
    reload,
  };
}

export type TicketActions = ReturnType<typeof useTicketActions>;
