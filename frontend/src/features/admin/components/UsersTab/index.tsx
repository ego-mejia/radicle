import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bot, Plus } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Avatar } from '../../../../components/ui/Avatar';
import { Badge } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { SettingsCard, SettingsParts as S } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useMe } from '../../../../hooks/useMe';
import { useToast } from '../../../../hooks/useToast';
import {
  adminKeys,
  createAgent,
  createUser,
  fetchUsers,
  patchUser,
} from '../../../../services/api/admin';
import type { User } from '../../../../services/api/types';
import { mcpSummary } from '../../../../lib/mcp';
import { McpPermissionsModal } from '../McpPermissionsModal';
import { NewUserModal, type NewPerson } from '../NewUserModal';
import { TokenReveal } from '../TokenReveal';

export function UsersTab() {
  const { t } = useTranslation();
  const me = useMe();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [reveal, setReveal] = useState<{ token: string; mcpUrl: string } | null>(null);
  const { data: users, isPending } = useQuery({ queryKey: adminKeys.users, queryFn: fetchUsers });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: adminKeys.users });
  const patch = useMutation({
    mutationFn: (v: {
      handle: string;
      body: { is_active?: boolean; is_instance_admin?: boolean };
    }) => patchUser(v.handle, v.body),
    onSuccess: refresh,
    onError: (error) => toast(errorMessage(error), 'error'),
  });

  if (isPending) return <PageSpinner />;
  const people = (users ?? []).filter((u) => u.kind !== 'system');
  const create = async (person: NewPerson) => {
    if (person.kind === 'agent') {
      const created = await createAgent({
        handle: person.handle,
        display_name: person.display_name,
        mcp_tools: person.mcp_tools,
      });
      setReveal({ token: created.token.token, mcpUrl: created.mcp_url });
    } else {
      const { handle, display_name, email, password } = person;
      await createUser({ handle, display_name, email, password });
    }
    refresh();
    toast(t('admin.userCreated', { handle: person.handle }));
  };

  return (
    <SettingsCard title={t('admin.users')} help={t('admin.usersHelp')}>
      {reveal && (
        <TokenReveal token={reveal.token} mcpUrl={reveal.mcpUrl} onClose={() => setReveal(null)} />
      )}
      <S.Rows>
        {people.map((user) => (
          <S.Row key={user.handle}>
            <S.Grow>
              <Avatar handle={user.handle} name={user.display_name} kind={user.kind} size={26} />
              {user.display_name}{' '}
              <small>
                @{user.handle}
                {user.email ? ` · ${user.email}` : ''}
              </small>
              {user.kind === 'agent' && (
                <Badge tone="accent">
                  <Bot size={12} /> {t('admin.kinds.agentShort')}
                </Badge>
              )}
              {user.kind === 'agent' && <small>{mcpSummary(t, user)}</small>}
              {user.is_instance_admin && <Badge tone="accent">{t('admin.instanceAdmin')}</Badge>}
              {!user.is_active && <Badge tone="danger">{t('admin.inactive')}</Badge>}
            </S.Grow>
            {user.kind === 'agent' && (
              <Button size="sm" onClick={() => setEditing(user)}>
                {t('admin.mcp.title')}
              </Button>
            )}
            {user.handle !== me.handle && (
              <>
                {user.kind === 'human' && (
                  <Button
                    size="sm"
                    onClick={() =>
                      patch.mutate({
                        handle: user.handle,
                        body: { is_instance_admin: !user.is_instance_admin },
                      })
                    }
                  >
                    {user.is_instance_admin ? t('admin.removeAdmin') : t('admin.makeAdmin')}
                  </Button>
                )}
                <Button
                  size="sm"
                  variant={user.is_active ? 'danger' : 'secondary'}
                  onClick={() =>
                    patch.mutate({ handle: user.handle, body: { is_active: !user.is_active } })
                  }
                >
                  {user.is_active ? t('admin.deactivate') : t('admin.activate')}
                </Button>
              </>
            )}
          </S.Row>
        ))}
      </S.Rows>
      <S.Actions>
        <Button variant="primary" onClick={() => setCreating(true)}>
          <Plus />
          {t('admin.newUser')}
        </Button>
      </S.Actions>
      {creating && (
        <NewUserModal kind="human" choose onClose={() => setCreating(false)} onCreate={create} />
      )}
      {editing && <McpPermissionsModal agent={editing} onClose={() => setEditing(null)} />}
    </SettingsCard>
  );
}
