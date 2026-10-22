import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Download, Puzzle, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button, IconButton } from '../../../../components/ui/Button';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { Field, FormError } from '../../../../components/ui/Field';
import { Textarea } from '../../../../components/ui/Input';
import { SettingsCard, SettingsParts as P } from '../../../../components/ui/SettingsCard';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import {
  deletePlugin,
  fetchPlugins,
  installExample,
  installPlugin,
  type Plugin,
  pluginKeys,
  setPluginEnabled,
} from '../../../../services/api/plugins';
import * as S from './style';

/** Admin, Plugins (ADR 0043): plugins that ship with Radicle, installing one from its
 * manifest, and turning installed ones off and on. */
export function PluginsTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [manifest, setManifest] = useState('');
  const [parseError, setParseError] = useState<string | null>(null);
  const [removing, setRemoving] = useState<Plugin | null>(null);
  const { data } = useQuery({ queryKey: pluginKeys.admin, queryFn: fetchPlugins });
  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: pluginKeys.admin });
    await queryClient.invalidateQueries({ queryKey: pluginKeys.blocks });
  };
  const example = useMutation({ mutationFn: installExample, onSuccess: refresh });
  const install = useMutation({
    mutationFn: installPlugin,
    onSuccess: async () => {
      setManifest('');
      await refresh();
    },
  });
  const toggle = useMutation({
    mutationFn: (p: Plugin) => setPluginEnabled(p.key, !p.enabled),
    onSuccess: refresh,
  });
  const remove = useMutation({ mutationFn: deletePlugin, onSuccess: refresh });
  const error = example.error ?? install.error ?? toggle.error ?? remove.error;

  const submit = () => {
    try {
      const parsed = JSON.parse(manifest) as Record<string, unknown>;
      setParseError(null);
      install.mutate(parsed);
    } catch {
      setParseError(t('plugins.notJson'));
    }
  };

  return (
    <S.Stack>
      <SettingsCard title={t('plugins.installed')} help={t('plugins.help')}>
        {data?.items.length === 0 && <P.Muted>{t('plugins.none')}</P.Muted>}
        <P.Rows>
          {data?.items.map((p) => (
            <P.Row key={p.key}>
              <P.Grow>
                <Puzzle size={16} />
                <strong>{p.name}</strong>
                <small>
                  {p.key} · {p.version}
                  {p.author && ` · ${p.author}`}
                </small>
                {!p.enabled && <Badge>{t('plugins.off')}</Badge>}
              </P.Grow>
              <Button size="sm" onClick={() => toggle.mutate(p)}>
                {t(p.enabled ? 'plugins.turnOff' : 'plugins.turnOn')}
              </Button>
              <IconButton
                label={t('plugins.delete', { name: p.name })}
                onClick={() => setRemoving(p)}
              >
                <Trash2 />
              </IconButton>
            </P.Row>
          ))}
        </P.Rows>
        <FormError>{error ? errorMessage(error) : null}</FormError>
      </SettingsCard>

      <SettingsCard title={t('plugins.examples')} help={t('plugins.examplesHelp')}>
        <P.Rows>
          {data?.examples.map((e) => (
            <P.Row key={e.key}>
              <P.Grow>
                <strong>{e.name}</strong>
                <small>{e.description}</small>
              </P.Grow>
              {e.installed ? (
                <Badge tone="accent">{t('plugins.isInstalled')}</Badge>
              ) : (
                <Button size="sm" onClick={() => example.mutate(e.key)}>
                  <Download aria-hidden />
                  {t('plugins.install')}
                </Button>
              )}
            </P.Row>
          ))}
        </P.Rows>
      </SettingsCard>

      <SettingsCard title={t('plugins.fromManifest')} help={t('plugins.manifestHelp')}>
        <S.Manifest
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <Field label={t('plugins.manifest')} error={parseError}>
            <Textarea
              rows={8}
              value={manifest}
              onChange={(e) => setManifest(e.target.value)}
              placeholder='{"key": "acme.widgets", "name": "…", "version": "1.0.0", "hooks": {…}}'
            />
          </Field>
          <S.Actions>
            <Button
              variant="primary"
              type="submit"
              disabled={!manifest.trim() || install.isPending}
            >
              {t('plugins.install')}
            </Button>
          </S.Actions>
        </S.Manifest>
      </SettingsCard>

      <ConfirmDialog
        open={!!removing}
        title={t('plugins.deleteTitle')}
        message={t('plugins.deleteMessage', { name: removing?.name ?? '' })}
        confirmLabel={t('common.delete')}
        onConfirm={() => {
          if (removing) remove.mutate(removing.key);
          setRemoving(null);
        }}
        onCancel={() => setRemoving(null)}
      />
    </S.Stack>
  );
}
