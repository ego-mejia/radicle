import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Lock, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { SettingsCard, SettingsParts as S } from '../../../../components/ui/SettingsCard';
import {
  createLevel,
  deleteLevel,
  fetchLevels,
  patchLevel,
  putGrants,
  securityKeys,
} from '../../../../services/api/security';
import type { ProjectDetail } from '../../../../services/api/types';
import { useSettingsMutation } from '../../hooks/useSettingsMutation';

const list = (text: string) =>
  text
    .split(',')
    .map((x) => x.trim().replace(/^@/, ''))
    .filter(Boolean);

/** Security levels: who sees restricted tickets (groups and people). */
export function LevelsSection({
  project,
  editable,
}: {
  project: ProjectDetail;
  editable: boolean;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const { data: levels = [] } = useQuery({
    queryKey: securityKeys.levels(project.key),
    queryFn: () => fetchLevels(project.key),
  });
  const refresh = () =>
    void queryClient.invalidateQueries({ queryKey: securityKeys.levels(project.key) });
  const create = useSettingsMutation(
    project.key,
    (n: string) => createLevel(project.key, { name: n }),
    refresh,
  );
  const patch = useSettingsMutation(
    project.key,
    (v: { id: string; include_participants: boolean }) =>
      patchLevel(v.id, { include_participants: v.include_participants }),
    refresh,
  );
  const grants = useSettingsMutation(
    project.key,
    (v: { id: string; groups: string[]; users: string[] }) =>
      putGrants(v.id, { groups: v.groups, users: v.users }),
    refresh,
  );
  const remove = useSettingsMutation(project.key, (id: string) => deleteLevel(id), refresh);
  return (
    <SettingsCard title={t('security.levels')} help={t('security.levelsHelp')}>
      <S.Rows>
        {levels.length === 0 && <S.Muted>{t('security.noLevels')}</S.Muted>}
        {levels.map((level) => (
          <S.Row key={level.id} aria-label={level.name}>
            <S.Grow>
              <Lock size={14} />
              <strong>{level.name}</strong>
              <small>{t('security.ticketCount', { count: level.ticket_count })}</small>
            </S.Grow>
            <Field label={t('security.groups')}>
              <Input
                defaultValue={level.groups.join(', ')}
                disabled={!editable}
                placeholder="equipo-legal"
                onBlur={(e) =>
                  e.target.value !== level.groups.join(', ') &&
                  grants.mutate({ id: level.id, groups: list(e.target.value), users: level.users })
                }
              />
            </Field>
            <Field label={t('security.users')}>
              <Input
                defaultValue={level.users.join(', ')}
                disabled={!editable}
                placeholder="ana, luis"
                onBlur={(e) =>
                  e.target.value !== level.users.join(', ') &&
                  grants.mutate({ id: level.id, groups: level.groups, users: list(e.target.value) })
                }
              />
            </Field>
            <label>
              <input
                type="checkbox"
                checked={level.include_participants}
                disabled={!editable}
                onChange={(e) =>
                  patch.mutate({ id: level.id, include_participants: e.target.checked })
                }
              />
              {t('security.participants')}
            </label>
            {editable && (
              <IconButton
                label={t('security.delete', { name: level.name })}
                onClick={() => remove.mutate(level.id)}
              >
                <Trash2 />
              </IconButton>
            )}
          </S.Row>
        ))}
      </S.Rows>
      {editable && (
        <S.Inline
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim()) create.mutate(name.trim(), { onSuccess: () => setName('') });
          }}
        >
          <Field label={t('security.newLevel')}>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Legal confidencial"
            />
          </Field>
          <Button type="submit" variant="primary" disabled={!name.trim()}>
            {t('common.add')}
          </Button>
        </S.Inline>
      )}
    </SettingsCard>
  );
}
