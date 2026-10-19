import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from '@tanstack/react-router';
import { Plus } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { Input } from '../../../../components/ui/Input';
import { SettingsCard, SettingsParts as S } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  createTemplate,
  fetchTemplates,
  setTemplateArchived,
  templateKeys,
} from '../../../../services/api/templates';

/** Templates with their linked projects and version; create, archive and open the editor. */
export function TemplatesTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [name, setName] = useState('');
  const { data: templates, isPending } = useQuery({
    queryKey: templateKeys.list(true),
    queryFn: () => fetchTemplates(true),
  });
  const create = useMutation({
    mutationFn: () => createTemplate({ name }),
    onSuccess: async (template) => {
      await queryClient.invalidateQueries({ queryKey: templateKeys.all });
      setName('');
      await navigate({ to: '/admin/templates/$id', params: { id: template.id }, search: {} });
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const archive = useMutation({
    mutationFn: (v: { id: string; archived: boolean }) => setTemplateArchived(v.id, v.archived),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: templateKeys.all }),
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  if (isPending) return <PageSpinner />;
  return (
    <SettingsCard title={t('admin.templates')} help={t('templates.help')}>
      <S.Rows>
        {(templates ?? []).map((tpl) => (
          <S.Row key={tpl.id}>
            <S.Grow>
              <Link to="/admin/templates/$id" params={{ id: tpl.id }} search={{}}>
                {tpl.name}
              </Link>
              <Badge tone="accent">v{tpl.version}</Badge>
              {tpl.is_default && <Badge>{t('templates.default')}</Badge>}
              {tpl.archived && <Badge tone="warning">{t('projects.archived')}</Badge>}
              <small>
                {tpl.linked_projects.length
                  ? tpl.linked_projects
                      .map((p) => (p.in_sync ? p.key : `${p.key} (v${p.template_version ?? '?'})`))
                      .join(', ')
                  : t('templates.noLinked')}
              </small>
            </S.Grow>
            {!tpl.is_default && (
              <Button
                size="sm"
                variant={tpl.archived ? 'secondary' : 'ghost'}
                onClick={() => archive.mutate({ id: tpl.id, archived: !tpl.archived })}
              >
                {tpl.archived ? t('settings.unarchive') : t('settings.archive')}
              </Button>
            )}
          </S.Row>
        ))}
      </S.Rows>
      <S.Inline
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim()) create.mutate();
        }}
      >
        <Input
          aria-label={t('templates.newName')}
          placeholder={t('templates.newName')}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Button type="submit" variant="primary" disabled={!name.trim() || create.isPending}>
          <Plus />
          {t('templates.create')}
        </Button>
      </S.Inline>
    </SettingsCard>
  );
}
