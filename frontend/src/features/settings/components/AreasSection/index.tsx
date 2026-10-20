import { useQuery } from '@tanstack/react-query';
import { Archive, ArchiveRestore } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AreaIcon } from '../../../../components/icons/AreaIcon';
import { Badge } from '../../../../components/ui/Badge';
import { Button, IconButton } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { api, unwrap } from '../../../../services/api/client';
import { createArea, patchArea } from '../../../../services/api/projects';
import type { ProjectDetail } from '../../../../services/api/types';
import { useSettingsMutation } from '../../hooks/useSettingsMutation';
import { AreaIconPicker } from '../AreaIconPicker';
import { SettingsCard, SettingsParts as S } from '../../../../components/ui/SettingsCard';

const DEFAULT_COLOR = '#4D7C0F';

export function AreasSection({ project, isAdmin }: { project: ProjectDetail; isAdmin: boolean }) {
  const { t } = useTranslation();
  const [name, setName] = useState('');
  const { data: areas = project.areas, refetch } = useQuery({
    queryKey: ['areas', project.key, project.areas.length],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/projects/{key}/areas', {
          params: { path: { key: project.key }, query: { include_archived: true } },
        }),
      ).items,
  });
  const done = () => void refetch();
  const create = useSettingsMutation(
    project.key,
    (n: string) => createArea(project.key, { name: n, color: DEFAULT_COLOR }),
    done,
  );
  const patch = useSettingsMutation(
    project.key,
    (v: {
      name: string;
      body: { name?: string; color?: string; icon?: string | null; archived?: boolean };
    }) => patchArea(project.key, v.name, v.body),
    done,
  );
  const editable = isAdmin && !project.archived;

  return (
    <SettingsCard title={t('settings.areas')} help={t('settings.areasHelp')}>
      <S.Rows>
        {areas.map((area) => (
          <S.Row key={area.name}>
            {editable ? (
              <AreaIconPicker
                area={area.name}
                icon={area.icon}
                color={area.color}
                onPick={(icon) => patch.mutate({ name: area.name, body: { icon } })}
              />
            ) : (
              <AreaIcon icon={area.icon} color={area.color} size={18} />
            )}
            {editable ? (
              <S.Swatch
                type="color"
                aria-label={`${t('settings.color')} ${area.name}`}
                defaultValue={area.color ?? DEFAULT_COLOR}
                onBlur={(e) =>
                  e.target.value.toUpperCase() !== area.color &&
                  patch.mutate({ name: area.name, body: { color: e.target.value } })
                }
              />
            ) : null}
            <S.Grow>
              {editable ? (
                <Input
                  defaultValue={area.name}
                  aria-label={t('settings.areaName')}
                  onBlur={(e) =>
                    e.target.value.trim() &&
                    e.target.value.trim() !== area.name &&
                    patch.mutate({ name: area.name, body: { name: e.target.value.trim() } })
                  }
                />
              ) : (
                area.name
              )}
              {area.archived && <Badge>{t('projects.archived')}</Badge>}
            </S.Grow>
            {editable && (
              <IconButton
                label={area.archived ? t('settings.restore') : t('settings.archive')}
                onClick={() =>
                  patch.mutate({ name: area.name, body: { archived: !area.archived } })
                }
              >
                {area.archived ? <ArchiveRestore /> : <Archive />}
              </IconButton>
            )}
          </S.Row>
        ))}
      </S.Rows>
      {editable && (
        <S.Inline
          onSubmit={(e) => {
            e.preventDefault();
            const value = name.trim();
            if (!value) return;
            // Clear right away so fast typing is not wiped when the request finishes.
            setName('');
            create.mutate(value, { onError: () => setName(value) });
          }}
        >
          <Field label={t('settings.newArea')}>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Backend" />
          </Field>
          <Button type="submit" variant="primary" disabled={!name.trim()}>
            {t('common.add')}
          </Button>
        </S.Inline>
      )}
    </SettingsCard>
  );
}
