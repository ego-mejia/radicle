import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { KeyRound, Pencil, PlugZap, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button, IconButton } from '../../../../components/ui/Button';
import { SettingsCard, SettingsParts as P } from '../../../../components/ui/SettingsCard';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import { accessKeys, fetchGroups } from '../../../../services/api/access';
import {
  createProvider,
  deleteProvider,
  fetchProviders,
  patchProvider,
  type ProviderInput,
  ssoKeys,
  testProvider,
} from '../../../../services/api/sso';
import { ProviderForm } from './components/ProviderForm';

/** OpenID Connect providers: one sign-in button each. */
export function SsoTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [editing, setEditing] = useState<string | 'new' | null>(null);
  const { data: providers = [] } = useQuery({
    queryKey: ssoKeys.providers,
    queryFn: fetchProviders,
  });
  const { data: groups = [] } = useQuery({ queryKey: accessKeys.groups, queryFn: fetchGroups });
  const groupNames = Object.fromEntries(groups.map((g) => [g.name, g.name]));
  const refresh = () => void queryClient.invalidateQueries({ queryKey: ssoKeys.providers });
  const save = useMutation({
    mutationFn: (v: { id?: string; body: ProviderInput }) =>
      v.id ? patchProvider(v.id, v.body) : createProvider(v.body),
    onSuccess: () => {
      setEditing(null);
      refresh();
    },
  });
  const remove = useMutation({ mutationFn: deleteProvider, onSuccess: refresh });
  const test = useMutation({
    mutationFn: testProvider,
    onSuccess: (r) =>
      toast(
        r.checks.map((c) => `${c.ok ? '✓' : '✗'} ${c.name}: ${c.detail}`).join('\n'),
        r.ok ? 'info' : 'error',
      ),
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  return (
    <SettingsCard title={t('sso.title')} help={t('sso.help')}>
      <P.Rows>
        {providers.map((p) =>
          editing === p.id ? (
            <ProviderForm
              key={p.id}
              initial={p}
              groupNames={groupNames}
              pending={save.isPending}
              error={save.error ? errorMessage(save.error) : null}
              onCancel={() => setEditing(null)}
              onSave={(body) => save.mutate({ id: p.id, body })}
            />
          ) : (
            <P.Row key={p.id}>
              <P.Grow>
                <KeyRound size={16} />
                <strong>{p.name}</strong>
                <small>{p.issuer_url}</small>
                {!p.enabled && <Badge>{t('sso.off')}</Badge>}
                {p.allowed_domains.length > 0 && <small>· {p.allowed_domains.join(', ')}</small>}
              </P.Grow>
              <IconButton label={t('sso.test', { name: p.name })} onClick={() => test.mutate(p.id)}>
                <PlugZap />
              </IconButton>
              <IconButton label={t('sso.edit', { name: p.name })} onClick={() => setEditing(p.id)}>
                <Pencil />
              </IconButton>
              <IconButton
                label={t('sso.delete', { name: p.name })}
                onClick={() => remove.mutate(p.id)}
              >
                <Trash2 />
              </IconButton>
            </P.Row>
          ),
        )}
      </P.Rows>
      {editing === 'new' ? (
        <ProviderForm
          groupNames={groupNames}
          pending={save.isPending}
          error={save.error ? errorMessage(save.error) : null}
          onCancel={() => setEditing(null)}
          onSave={(body) => save.mutate({ body })}
        />
      ) : (
        <Button size="sm" onClick={() => setEditing('new')}>
          <Plus />
          {t('sso.new')}
        </Button>
      )}
    </SettingsCard>
  );
}
