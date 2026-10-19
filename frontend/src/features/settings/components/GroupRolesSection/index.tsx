import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Users, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button, IconButton } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import { SettingsCard, SettingsParts as S } from '../../../../components/ui/SettingsCard';
import {
  accessKeys,
  fetchGroupRoles,
  putGroupRole,
  removeGroupRole,
} from '../../../../services/api/access';
import type { ProjectDetail, ProjectRole } from '../../../../services/api/types';
import { useSettingsMutation } from '../../hooks/useSettingsMutation';

const ROLES: ProjectRole[] = ['admin', 'member', 'viewer'];

/** Groups in the project: everyone in them gets the role (their highest role wins). */
export function GroupRolesSection({
  project,
  editable,
}: {
  project: ProjectDetail;
  editable: boolean;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [group, setGroup] = useState('');
  const [role, setRole] = useState<ProjectRole>('member');
  const { data: rows = [] } = useQuery({
    queryKey: accessKeys.groupRoles(project.key),
    queryFn: () => fetchGroupRoles(project.key),
  });
  const refresh = () =>
    void queryClient.invalidateQueries({ queryKey: accessKeys.groupRoles(project.key) });
  const put = useSettingsMutation(
    project.key,
    (v: { group: string; role: ProjectRole }) => putGroupRole(project.key, v.group, v.role),
    refresh,
  );
  const remove = useSettingsMutation(
    project.key,
    (g: string) => removeGroupRole(project.key, g),
    refresh,
  );
  return (
    <SettingsCard title={t('settings.groups')} help={t('settings.groupsHelp')}>
      <S.Rows>
        {rows.length === 0 && <S.Muted>{t('settings.noGroups')}</S.Muted>}
        {rows.map((r) => (
          <S.Row key={r.group}>
            <S.Grow>
              <Users size={16} />
              {r.group} <small>{t('settings.groupMembers', { count: r.member_count })}</small>
            </S.Grow>
            {editable ? (
              <>
                <Select
                  value={r.role}
                  aria-label={`${t('settings.role')} ${r.group}`}
                  onChange={(e) =>
                    put.mutate({ group: r.group, role: e.target.value as ProjectRole })
                  }
                >
                  {ROLES.map((x) => (
                    <option key={x} value={x}>
                      {t(`projects.roles.${x}`)}
                    </option>
                  ))}
                </Select>
                <IconButton
                  label={`${t('common.remove')} ${r.group}`}
                  onClick={() => remove.mutate(r.group)}
                >
                  <X />
                </IconButton>
              </>
            ) : (
              <Badge>{t(`projects.roles.${r.role}`)}</Badge>
            )}
          </S.Row>
        ))}
      </S.Rows>
      {editable && (
        <S.Inline
          onSubmit={(e) => {
            e.preventDefault();
            put.mutate({ group: group.trim(), role }, { onSuccess: () => setGroup('') });
          }}
        >
          <Field label={t('settings.addGroup')}>
            <Input
              value={group}
              onChange={(e) => setGroup(e.target.value)}
              placeholder="equipo-legal"
            />
          </Field>
          <Select
            value={role}
            onChange={(e) => setRole(e.target.value as ProjectRole)}
            aria-label={t('settings.groupRole')}
          >
            {ROLES.map((x) => (
              <option key={x} value={x}>
                {t(`projects.roles.${x}`)}
              </option>
            ))}
          </Select>
          <Button type="submit" variant="primary" disabled={!group.trim()}>
            {t('common.add')}
          </Button>
        </S.Inline>
      )}
    </SettingsCard>
  );
}
