import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
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
import { adminKeys, createUser, fetchUsers, patchUser } from '../../../../services/api/admin';
import { NewUserModal } from '../NewUserModal';

export function UsersTab() {
  const { t } = useTranslation();
  const me = useMe();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
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
  const humans = (users ?? []).filter((u) => u.kind === 'human');

  return (
    <SettingsCard title={t('admin.users')} help={t('admin.usersHelp')}>
      <S.Rows>
        {humans.map((user) => (
          <S.Row key={user.handle}>
            <S.Grow>
              <Avatar handle={user.handle} name={user.display_name} size={26} />
              {user.display_name}{' '}
              <small>
                @{user.handle} · {user.email}
              </small>
              {user.is_instance_admin && <Badge tone="accent">{t('admin.instanceAdmin')}</Badge>}
              {!user.is_active && <Badge tone="danger">{t('admin.inactive')}</Badge>}
            </S.Grow>
            {user.handle !== me.handle && (
              <>
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
        <NewUserModal
          kind="human"
          onClose={() => setCreating(false)}
          onCreate={async (person) => {
            await createUser(person);
            refresh();
            toast(t('admin.userCreated', { handle: person.handle }));
          }}
        />
      )}
    </SettingsCard>
  );
}
