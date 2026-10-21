import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from '@tanstack/react-router';
import { Archive, Pencil, Plus } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button, IconButton } from '../../../../components/ui/Button';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { SettingsCard, SettingsParts as P } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  archiveTemplate,
  createTemplate,
  fetchTemplates,
  folioKeys,
  type FolioTemplate,
} from '../../../../services/api/folio';
import { TEMPLATE_VARIABLES } from './variables';
import * as S from './style';

const KINDS = ['page', 'space'] as const;

/** Folio → Admin → Templates: Folio's own, the global ones and the spaces'. */
export function TemplatesAdmin() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [archiving, setArchiving] = useState<FolioTemplate | null>(null);
  const pages = useQuery({
    queryKey: folioKeys.templates('page'),
    queryFn: () => fetchTemplates('page'),
  });
  const spaces = useQuery({
    queryKey: folioKeys.templates('space'),
    queryFn: () => fetchTemplates('space'),
  });
  const lists = { page: pages.data, space: spaces.data };
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['folio', 'templates'] });

  const create = useMutation({
    mutationFn: (kind: (typeof KINDS)[number]) =>
      createTemplate(
        kind === 'page'
          ? { kind, name: t('folio.templates.untitled'), content_md: '' }
          : { kind, name: t('folio.templates.untitled'), structure: { pages: [] } },
      ),
    onSuccess: async (created) => {
      await refresh();
      await navigate({ to: '/folio/admin/templates/$id', params: { id: created.id } });
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const archive = useMutation({
    mutationFn: (id: string) => archiveTemplate(id),
    onSuccess: async () => {
      setArchiving(null);
      await refresh();
      toast(t('folio.templates.archived'));
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });

  return (
    <>
      {KINDS.map((kind) => (
        <SettingsCard
          key={kind}
          title={t(`folio.templates.kinds.${kind}`)}
          help={t(`folio.templates.help.${kind}`, TEMPLATE_VARIABLES)}
        >
          {lists[kind] ? (
            <P.Rows>
              {lists[kind].map((tpl) => (
                <P.Row key={tpl.id}>
                  <P.Grow>
                    <S.Icon aria-hidden>{tpl.icon ?? '📄'}</S.Icon>
                    <S.Name>
                      <Link to="/folio/admin/templates/$id" params={{ id: tpl.id }}>
                        {tpl.name}
                      </Link>
                      <small>{tpl.description}</small>
                    </S.Name>
                    {tpl.builtin && <Badge>{t('folio.templates.builtin')}</Badge>}
                    {tpl.space && <Badge>{tpl.space}</Badge>}
                  </P.Grow>
                  <IconButton
                    label={t('folio.templates.edit', { name: tpl.name })}
                    onClick={() =>
                      void navigate({ to: '/folio/admin/templates/$id', params: { id: tpl.id } })
                    }
                  >
                    <Pencil />
                  </IconButton>
                  <IconButton
                    label={t('folio.templates.archive', { name: tpl.name })}
                    onClick={() => setArchiving(tpl)}
                  >
                    <Archive />
                  </IconButton>
                </P.Row>
              ))}
              {lists[kind].length === 0 && <P.Muted>{t('folio.templates.none')}</P.Muted>}
              <P.Actions>
                <Button onClick={() => create.mutate(kind)} disabled={create.isPending}>
                  <Plus aria-hidden />
                  {t(`folio.templates.new.${kind}`)}
                </Button>
              </P.Actions>
            </P.Rows>
          ) : (
            <PageSpinner />
          )}
        </SettingsCard>
      ))}
      <ConfirmDialog
        open={archiving !== null}
        title={t('folio.templates.archiveTitle', { name: archiving?.name ?? '' })}
        message={t('folio.templates.archiveText')}
        confirmLabel={t('folio.templates.archiveConfirm')}
        onConfirm={() => archiving && archive.mutate(archiving.id)}
        onCancel={() => setArchiving(null)}
      />
    </>
  );
}
