import { Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../../../../../components/ui/Button';
import { Field, FormError } from '../../../../../../../../components/ui/Field';
import { Input } from '../../../../../../../../components/ui/Input';
import type { ChatIntegrationInput } from '../../../../../../../../services/api/integrations';
import { EventPicker } from '../../../EventPicker';
import * as S from './style';

type Kind = 'slack' | 'teams';
type RouteDraft = { channel: string; events: string[]; space: string };
type Props = {
  pending: boolean;
  error: string | null;
  onSave: (body: ChatIntegrationInput) => void;
  onCancel: () => void;
};

const scope = (space: string): Record<string, string> => (space ? { space } : {});

/** A new Slack workspace or Teams team: credentials and the channels that hear events. */
export function ChatForm({ pending, error, onSave, onCancel }: Props) {
  const { t } = useTranslation();
  const [kind, setKind] = useState<Kind>('slack');
  const [name, setName] = useState('');
  const [botToken, setBotToken] = useState('');
  const [signing, setSigning] = useState('');
  const [secret, setSecret] = useState('');
  const [routes, setRoutes] = useState<RouteDraft[]>([]);
  const patch = (n: number, change: Partial<RouteDraft>) =>
    setRoutes(routes.map((r, i) => (i === n ? { ...r, ...change } : r)));
  const credentials: Record<string, string> =
    kind === 'slack' ? { bot_token: botToken, signing_secret: signing } : { secret };
  const submit = () =>
    onSave({
      kind,
      name,
      credentials,
      notices: routes.map((r) => ({
        channel: r.channel,
        events: r.events,
        filter: scope(r.space),
      })),
      active: true,
    });
  return (
    <S.Form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <S.Kinds role="radiogroup" aria-label={t('integrations.kind')}>
        {(['slack', 'teams'] as const).map((k) => (
          <label key={k}>
            <input type="radio" checked={kind === k} onChange={() => setKind(k)} />
            {t(`integrations.${k}`)}
          </label>
        ))}
      </S.Kinds>
      <S.Grid>
        <Field label={t('integrations.name')}>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme" />
        </Field>
        {kind === 'slack' ? (
          <>
            <Field label={t('integrations.botToken')} hint={t('integrations.botTokenHint')}>
              <Input
                type="password"
                value={botToken}
                onChange={(e) => setBotToken(e.target.value)}
              />
            </Field>
            <Field label={t('integrations.signingSecret')}>
              <Input type="password" value={signing} onChange={(e) => setSigning(e.target.value)} />
            </Field>
          </>
        ) : (
          <Field label={t('integrations.teamsSecret')} hint={t('integrations.teamsSecretHint')}>
            <Input type="password" value={secret} onChange={(e) => setSecret(e.target.value)} />
          </Field>
        )}
      </S.Grid>
      {routes.map((r, n) => (
        <S.Route key={n}>
          <S.Grid>
            <Field
              label={t('integrations.channel', { n: n + 1 })}
              hint={t(
                kind === 'slack'
                  ? 'integrations.slackChannelHint'
                  : 'integrations.teamsChannelHint',
              )}
            >
              <Input value={r.channel} onChange={(e) => patch(n, { channel: e.target.value })} />
            </Field>
            <Field label={t('integrations.space')} hint={t('integrations.spaceHint')}>
              <Input value={r.space} onChange={(e) => patch(n, { space: e.target.value })} />
            </Field>
            <IconButton
              label={t('integrations.removeChannel', { n: n + 1 })}
              onClick={() => setRoutes(routes.filter((_, i) => i !== n))}
            >
              <Trash2 />
            </IconButton>
          </S.Grid>
          <EventPicker value={r.events} onChange={(events) => patch(n, { events })} />
        </S.Route>
      ))}
      <div>
        <Button
          size="sm"
          onClick={() => setRoutes([...routes, { channel: '', events: [], space: '' }])}
        >
          <Plus />
          {t('integrations.addChannel')}
        </Button>
      </div>
      <FormError>{error}</FormError>
      <S.Row>
        <Button type="submit" variant="primary" disabled={pending || !name}>
          {t('common.save')}
        </Button>
        <Button onClick={onCancel}>{t('common.cancel')}</Button>
      </S.Row>
    </S.Form>
  );
}
