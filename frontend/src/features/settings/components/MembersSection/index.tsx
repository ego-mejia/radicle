import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Avatar } from '../../../../components/ui/Avatar';
import { Badge } from '../../../../components/ui/Badge';
import { IconButton } from '../../../../components/ui/Button';
import { Select } from '../../../../components/ui/Input';
import { putMember, removeMember } from '../../../../services/api/projects';
import type { ProjectDetail, ProjectRole } from '../../../../services/api/types';
import { useSettingsMutation } from '../../hooks/useSettingsMutation';
import { MemberPicker } from '../MemberPicker';
import { SettingsCard, SettingsParts as S } from '../../../../components/ui/SettingsCard';

const ROLES: ProjectRole[] = ['admin', 'member', 'viewer'];

export function MembersSection({ project, isAdmin }: { project: ProjectDetail; isAdmin: boolean }) {
  const { t } = useTranslation();
  const put = useSettingsMutation(project.key, (v: { handle: string; role: ProjectRole }) =>
    putMember(project.key, v.handle, v.role),
  );
  const remove = useSettingsMutation(project.key, (h: string) => removeMember(project.key, h));
  const editable = isAdmin && !project.archived;

  return (
    <SettingsCard title={t('settings.members')} help={t('settings.membersHelp')}>
      <S.Rows>
        {project.members.map((m) => (
          <S.Row key={m.handle}>
            <S.Grow>
              <Avatar handle={m.handle} name={m.display_name} kind={m.kind} size={26} />
              {m.display_name} <small>@{m.handle}</small>
              {m.kind === 'agent' && <Badge tone="accent">agent</Badge>}
            </S.Grow>
            {m.groups.length > 0 && (
              <S.Muted>{t('settings.viaGroups', { groups: m.groups.join(', ') })}</S.Muted>
            )}
            {m.role !== m.effective_role && (
              <Badge tone="accent" title={t('settings.effectiveRole')}>
                {t(`projects.roles.${m.effective_role}`)}
              </Badge>
            )}
            {editable && m.role ? (
              <>
                <Select
                  value={m.role}
                  aria-label={`${t('settings.role')} @${m.handle}`}
                  onChange={(e) =>
                    put.mutate({ handle: m.handle, role: e.target.value as ProjectRole })
                  }
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {t(`projects.roles.${r}`)}
                    </option>
                  ))}
                </Select>
                <IconButton
                  label={`${t('common.remove')} @${m.handle}`}
                  onClick={() => remove.mutate(m.handle)}
                >
                  <X />
                </IconButton>
              </>
            ) : (
              m.role && <Badge>{t(`projects.roles.${m.role}`)}</Badge>
            )}
          </S.Row>
        ))}
      </S.Rows>
      {editable && <MemberPicker projectKey={project.key} />}
    </SettingsCard>
  );
}
