import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { FormError } from '../../../../components/ui/Field';
import { Modal } from '../../../../components/ui/Modal';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { adminKeys, patchUser } from '../../../../services/api/admin';
import type { User } from '../../../../services/api/types';
import { McpToolPicker } from '../McpToolPicker';

type Props = { agent: User; onClose: () => void };

/** Edit which MCP tools an agent may call. */
export function McpPermissionsModal({ agent, onClose }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [tools, setTools] = useState<string[] | null>(agent.mcp_tools ?? null);
  const save = useMutation({
    mutationFn: () => patchUser(agent.handle, { mcp_tools: tools }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: adminKeys.users });
      toast(t('admin.mcp.saved', { handle: agent.handle }));
      onClose();
    },
  });
  return (
    <Modal
      open
      width={760}
      onOpenChange={(open) => !open && onClose()}
      title={t('admin.mcp.titleFor', { name: agent.display_name })}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button variant="primary" onClick={() => save.mutate()} disabled={save.isPending}>
            {t('common.save')}
          </Button>
        </>
      }
    >
      <p>{t('admin.mcp.help')}</p>
      <McpToolPicker value={tools} onChange={setTools} />
      <FormError>{save.error ? errorMessage(save.error) : null}</FormError>
    </Modal>
  );
}
