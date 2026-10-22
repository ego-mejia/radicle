import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { History, PlugZap, Plus, RotateCw, Trash2, Webhook as WebhookIcon } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../../../components/ui/Badge';
import { Button, IconButton } from '../../../../../../components/ui/Button';
import { Field, FormError } from '../../../../../../components/ui/Field';
import { Input } from '../../../../../../components/ui/Input';
import { SettingsCard, SettingsParts as P } from '../../../../../../components/ui/SettingsCard';
import { useErrorMessage } from '../../../../../../hooks/useErrorMessage';
import {
  createWebhook,
  deleteWebhook,
  fetchDeliveries,
  fetchWebhooks,
  integrationKeys,
  pingWebhook,
  rotateWebhookSecret,
  type Webhook,
} from '../../../../../../services/api/integrations';
import { EventPicker } from '../EventPicker';
import * as S from './style';

function Deliveries({ hook }: { hook: Webhook }) {
  const { t } = useTranslation();
  const { data: rows = [] } = useQuery({
    queryKey: integrationKeys.deliveries(hook.id),
    queryFn: () => fetchDeliveries(hook.id),
  });
  if (!rows.length) return <P.Muted>{t('integrations.noDeliveries')}</P.Muted>;
  return (
    <S.Log aria-label={t('integrations.deliveries', { name: hook.name })}>
      {rows.map((d) => (
        <li key={d.id}>
          <Badge
            tone={d.status === 'sent' ? 'accent' : d.status === 'failed' ? 'danger' : 'neutral'}
          >
            {t(`integrations.status.${d.status}`)}
          </Badge>
          <code>{d.event}</code>
          <small>
            {d.response_status ?? '—'} · {t('integrations.attempts', { count: d.attempts })}
          </small>
          {d.last_error && <S.Error>{d.last_error}</S.Error>}
        </li>
      ))}
    </S.Log>
  );
}

/** Webhooks: public events POSTed to a receiver, signed with HMAC (Folio 5.5). */
export function WebhooksCard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [adding, setAdding] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const [secret, setSecret] = useState<{ name: string; value: string } | null>(null);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [events, setEvents] = useState<string[]>([]);
  const [space, setSpace] = useState('');
  const { data: hooks = [] } = useQuery({
    queryKey: integrationKeys.webhooks,
    queryFn: fetchWebhooks,
  });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: integrationKeys.webhooks });
  const create = useMutation({
    mutationFn: () =>
      createWebhook({ name, url, events, filter: space ? { space } : {}, active: true }),
    onSuccess: (made) => {
      setSecret({ name: made.name, value: made.secret });
      setAdding(false);
      setName('');
      setUrl('');
      setEvents([]);
      setSpace('');
      refresh();
    },
  });
  const remove = useMutation({ mutationFn: deleteWebhook, onSuccess: refresh });
  const ping = useMutation({
    mutationFn: pingWebhook,
    onSuccess: (_, id) => {
      setOpen(id);
      void queryClient.invalidateQueries({ queryKey: integrationKeys.deliveries(id) });
    },
  });
  const rotate = useMutation({
    mutationFn: (hook: Webhook) => rotateWebhookSecret(hook.id).then((value) => ({ hook, value })),
    onSuccess: ({ hook, value }) => setSecret({ name: hook.name, value }),
  });
  return (
    <SettingsCard title={t('integrations.webhooks')} help={t('integrations.webhooksHelp')}>
      {secret && (
        <S.Secret role="status">
          {t('integrations.secretOnce', { name: secret.name })}
          <code>{secret.value}</code>
          <Button size="sm" onClick={() => setSecret(null)}>
            {t('common.close')}
          </Button>
        </S.Secret>
      )}
      <P.Rows>
        {hooks.map((h) => (
          <div key={h.id}>
            <P.Row>
              <P.Grow>
                <WebhookIcon size={16} />
                <strong>{h.name}</strong>
                <small>{h.url}</small>
                {!h.active && <Badge>{t('integrations.off')}</Badge>}
                <small>
                  · {h.events.length ? h.events.join(', ') : t('integrations.allEvents')}
                </small>
              </P.Grow>
              <IconButton
                label={t('integrations.ping', { name: h.name })}
                onClick={() => ping.mutate(h.id)}
              >
                <PlugZap />
              </IconButton>
              <IconButton
                label={t('integrations.log', { name: h.name })}
                onClick={() => setOpen(open === h.id ? null : h.id)}
              >
                <History />
              </IconButton>
              <IconButton
                label={t('integrations.rotate', { name: h.name })}
                onClick={() => rotate.mutate(h)}
              >
                <RotateCw />
              </IconButton>
              <IconButton
                label={t('integrations.delete', { name: h.name })}
                onClick={() => remove.mutate(h.id)}
              >
                <Trash2 />
              </IconButton>
            </P.Row>
            {open === h.id && <Deliveries hook={h} />}
          </div>
        ))}
      </P.Rows>
      {adding ? (
        <S.Form
          onSubmit={(e) => {
            e.preventDefault();
            create.mutate();
          }}
        >
          <S.Grid>
            <Field label={t('integrations.name')}>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="CI" />
            </Field>
            <Field label={t('integrations.url')} hint={t('integrations.urlHint')}>
              <Input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://ci.example.com/radicle"
              />
            </Field>
            <Field label={t('integrations.space')} hint={t('integrations.spaceHint')}>
              <Input value={space} onChange={(e) => setSpace(e.target.value)} placeholder="eng" />
            </Field>
          </S.Grid>
          <EventPicker value={events} onChange={setEvents} />
          <FormError>{create.error ? errorMessage(create.error) : null}</FormError>
          <S.Row>
            <Button type="submit" variant="primary" disabled={create.isPending || !name || !url}>
              {t('common.save')}
            </Button>
            <Button onClick={() => setAdding(false)}>{t('common.cancel')}</Button>
          </S.Row>
        </S.Form>
      ) : (
        <Button size="sm" onClick={() => setAdding(true)}>
          <Plus />
          {t('integrations.newWebhook')}
        </Button>
      )}
    </SettingsCard>
  );
}
