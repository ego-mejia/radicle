import { useQuery } from '@tanstack/react-query';
import { Archive, ArchiveRestore, Pencil, Plus } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button, IconButton } from '../../../../components/ui/Button';
import { SettingsCard, SettingsParts } from '../../../../components/ui/SettingsCard';
import { fetchFields, fieldKeys, patchField } from '../../../../services/api/fields';
import type { CustomField, ProjectDetail } from '../../../../services/api/types';
import { useSettingsMutation } from '../../hooks/useSettingsMutation';
import { FieldModal } from './components/FieldModal';
import * as S from './style';

type Props = { project: ProjectDetail; isAdmin: boolean; locked?: boolean };

/** Custom fields of a project: list, create, edit, archive and restore. */
export function CustomFieldsSection({ project, isAdmin, locked }: Props) {
  const { t } = useTranslation();
  const [editing, setEditing] = useState<CustomField | 'new' | null>(null);
  const { data: fields = [], refetch } = useQuery({
    queryKey: fieldKeys.list(project.key, true),
    queryFn: () => fetchFields(project.key, true),
  });
  const archive = useSettingsMutation(
    project.key,
    (f: CustomField) => patchField(project.key, f.key, { archived: !f.archived }),
    () => void refetch(),
  );
  const editable = isAdmin && !project.archived && !locked;

  return (
    <SettingsCard
      title={t('fields.title')}
      help={
        locked
          ? t('fields.lockedHelp', { template: project.template?.name ?? '' })
          : t('fields.help')
      }
    >
      {fields.length === 0 ? (
        <S.Empty>{t('fields.empty')}</S.Empty>
      ) : (
        <SettingsParts.Rows>
          {fields.map((f) => (
            <SettingsParts.Row key={f.key}>
              <SettingsParts.Grow>
                <S.Name $archived={f.archived}>{f.name}</S.Name>
                <S.Key>cf.{f.key}</S.Key>
                <Badge>{t(`fields.types.${f.field_type}`)}</Badge>
                {f.archived && <Badge>{t('projects.archived')}</Badge>}
              </SettingsParts.Grow>
              <S.Scope>
                {f.applies_to_types.map((type) => t(`ticket.types.${type}`)).join(', ')}
                {f.applies_to_areas && ` · ${f.applies_to_areas.join(', ')}`}
              </S.Scope>
              {editable && (
                <>
                  <IconButton label={t('common.edit')} onClick={() => setEditing(f)}>
                    <Pencil />
                  </IconButton>
                  <IconButton
                    label={f.archived ? t('settings.restore') : t('settings.archive')}
                    onClick={() => archive.mutate(f)}
                  >
                    {f.archived ? <ArchiveRestore /> : <Archive />}
                  </IconButton>
                </>
              )}
            </SettingsParts.Row>
          ))}
        </SettingsParts.Rows>
      )}
      {editable && (
        <SettingsParts.Actions>
          <Button onClick={() => setEditing('new')}>
            <Plus />
            {t('fields.new')}
          </Button>
        </SettingsParts.Actions>
      )}
      {editing && (
        <FieldModal
          project={project}
          field={editing === 'new' ? null : editing}
          onClose={() => {
            setEditing(null);
            void refetch();
          }}
        />
      )}
    </SettingsCard>
  );
}
