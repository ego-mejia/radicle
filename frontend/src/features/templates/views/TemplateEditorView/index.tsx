import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useParams, useSearch } from '@tanstack/react-router';
import { ArrowLeft } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { Field } from '../../../../components/ui/Field';
import { Input, Textarea } from '../../../../components/ui/Input';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { Tabs } from '../../../../components/ui/Tabs';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useMe } from '../../../../hooks/useMe';
import { useToast } from '../../../../hooks/useToast';
import { removedStatuses, workflowErrors } from '../../../../lib/workflow';
import {
  fetchTemplate,
  type Mappings,
  patchTemplate,
  templateKeys,
} from '../../../../services/api/templates';
import {
  TICKET_TYPES,
  type TemplateConfig,
  type TemplateDetail,
  type TicketType,
} from '../../../../services/api/types';
import { AreasTagsEditor } from '../../components/AreasTagsEditor';
import { ConfigFieldsEditor } from '../../components/ConfigFieldsEditor';
import { MappingDialog, type Removed } from '../../components/MappingDialog';
import { SyncRuns } from '../../components/SyncRuns';
import { WorkflowEditor } from '../../components/WorkflowEditor';
import * as S from './style';

type Tab = 'general' | 'workflows' | 'fields' | 'sync';
const TABS: Tab[] = ['general', 'workflows', 'fields', 'sync'];

export function TemplateEditorView() {
  const { t } = useTranslation();
  const { id } = useParams({ from: '/app/admin/templates/$id' });
  const { data: template, isPending } = useQuery({
    queryKey: templateKeys.detail(id),
    queryFn: () => fetchTemplate(id),
  });
  if (isPending) return <PageSpinner />;
  if (!template) return <EmptyState plant="seed" title={t('templates.notFound')} />;
  return <Editor key={`${template.id}-${template.version}`} template={template} />;
}

function Editor({ template }: { template: TemplateDetail }) {
  const { t } = useTranslation();
  const me = useMe();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const navigate = useNavigate({ from: '/admin/templates/$id' });
  const { tab, type } = useSearch({ from: '/app/admin/templates/$id' });
  const current = (TABS.includes(tab as Tab) ? tab : 'workflows') as Tab;
  const ticketType = (TICKET_TYPES.includes(type as TicketType) ? type : 'task') as TicketType;
  const [config, setConfig] = useState<TemplateConfig>(template.config);
  const [name, setName] = useState(template.name);
  const [description, setDescription] = useState(template.description_md);
  const [mapping, setMapping] = useState<{ removed: Removed[]; detail?: string } | null>(null);
  const readOnly = !me.is_instance_admin || template.archived;
  const dirty =
    JSON.stringify(config) !== JSON.stringify(template.config) ||
    name !== template.name ||
    description !== template.description_md;
  const invalid = TICKET_TYPES.some((tt) => workflowErrors(config.workflows[tt]!).length > 0);

  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [dirty]);

  const save = useMutation({
    mutationFn: (mappings: Mappings | null) =>
      patchTemplate(template.id, {
        name,
        description_md: description,
        config,
        status_mappings: mappings,
      }),
    onSuccess: async (saved) => {
      setMapping(null);
      queryClient.setQueryData(templateKeys.detail(template.id), saved);
      await queryClient.invalidateQueries({ queryKey: templateKeys.all });
      toast(
        saved.version > template.version
          ? t('templates.savedVersion', { version: saved.version })
          : t('profile.saved'),
      );
      saved.warnings?.forEach((w) => toast(w, 'warning'));
      if (saved.version > template.version) void navigate({ search: { tab: 'sync' } });
    },
    onError: (error) => toast(errorMessage(error), 'error'),
  });

  const removed: Removed[] = TICKET_TYPES.flatMap((tt) =>
    removedStatuses(template.config.workflows[tt]!, config.workflows[tt]!).map((status) => ({
      type: tt,
      status,
    })),
  );

  return (
    <>
      <S.Header>
        <Link to="/admin" search={{ tab: 'templates' }}>
          <ArrowLeft size={16} /> {t('admin.templates')}
        </Link>
        <S.Title>
          <h1>{template.name}</h1>
          <Badge tone="accent">v{template.version}</Badge>
          {template.archived && <Badge>{t('projects.archived')}</Badge>}
        </S.Title>
        <S.Linked>
          {template.linked_projects.length
            ? t('templates.linkedTo', {
                projects: template.linked_projects.map((p) => p.key).join(', '),
              })
            : t('templates.noLinked')}
        </S.Linked>
        {!readOnly && (
          <S.Actions>
            <Button
              disabled={!dirty || save.isPending}
              onClick={() => {
                setConfig(template.config);
                setName(template.name);
                setDescription(template.description_md);
              }}
            >
              {t('templates.discard')}
            </Button>
            <Button
              variant="primary"
              disabled={!dirty || invalid || save.isPending}
              onClick={() => (removed.length ? setMapping({ removed }) : save.mutate(null))}
            >
              {t('common.save')}
            </Button>
          </S.Actions>
        )}
      </S.Header>
      <S.Body>
        <Tabs
          label={t('templates.editor')}
          value={current}
          onChange={(next) => void navigate({ search: { tab: next, type: ticketType } })}
          tabs={TABS.map((value) => ({ id: value, label: t(`templates.tabs.${value}`) }))}
        />
        {current === 'general' && (
          <S.Panel>
            <Field label={t('fields.name')}>
              <Input value={name} disabled={readOnly} onChange={(e) => setName(e.target.value)} />
            </Field>
            <Field label={t('projects.description')}>
              <Textarea
                value={description}
                disabled={readOnly}
                onChange={(e) => setDescription(e.target.value)}
              />
            </Field>
            <AreasTagsEditor config={config} onChange={setConfig} readOnly={readOnly} />
          </S.Panel>
        )}
        {current === 'workflows' && (
          <S.Panel>
            <Tabs
              label={t('settings.workflows')}
              value={ticketType}
              onChange={(next) => void navigate({ search: { tab: 'workflows', type: next } })}
              tabs={TICKET_TYPES.map((value) => ({ id: value, label: t(`ticket.types.${value}`) }))}
            />
            <WorkflowEditor
              key={ticketType}
              value={config.workflows[ticketType]!}
              readOnly={readOnly}
              onChange={(workflow) =>
                setConfig({ ...config, workflows: { ...config.workflows, [ticketType]: workflow } })
              }
            />
          </S.Panel>
        )}
        {current === 'fields' && (
          <S.Panel>
            <ConfigFieldsEditor
              fields={config.custom_fields ?? []}
              readOnly={readOnly}
              onChange={(custom_fields) => setConfig({ ...config, custom_fields })}
            />
          </S.Panel>
        )}
        {current === 'sync' && (
          <S.Panel>
            <SyncRuns templateId={template.id} />
          </S.Panel>
        )}
      </S.Body>
      {mapping && (
        <MappingDialog
          removed={mapping.removed}
          targets={Object.fromEntries(
            TICKET_TYPES.map((tt) => [tt, config.workflows[tt]!.statuses]),
          )}
          pending={save.isPending}
          onConfirm={(mappings) => save.mutate(mappings)}
          onClose={() => setMapping(null)}
        />
      )}
    </>
  );
}
