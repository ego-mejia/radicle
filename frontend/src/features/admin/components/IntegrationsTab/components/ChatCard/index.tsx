import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { MessageSquare, Plus, Send, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../../../components/ui/Badge';
import { Button, IconButton } from '../../../../../../components/ui/Button';
import { SettingsCard, SettingsParts as P } from '../../../../../../components/ui/SettingsCard';
import { useErrorMessage } from '../../../../../../hooks/useErrorMessage';
import { useToast } from '../../../../../../hooks/useToast';
import {
  createChatIntegration,
  deleteChatIntegration,
  fetchChatIntegrations,
  integrationKeys,
  testChatIntegration,
} from '../../../../../../services/api/integrations';
import { ChatForm } from './components/ChatForm';
import * as S from './style';

/** Slack and Teams: notices on channels and `/radicle search` / `ask` (Folio 5.4). */
export function ChatCard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [adding, setAdding] = useState(false);
  const { data: chats = [] } = useQuery({
    queryKey: integrationKeys.chats,
    queryFn: fetchChatIntegrations,
  });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: integrationKeys.chats });
  const create = useMutation({
    mutationFn: createChatIntegration,
    onSuccess: () => {
      setAdding(false);
      refresh();
    },
  });
  const remove = useMutation({ mutationFn: deleteChatIntegration, onSuccess: refresh });
  const test = useMutation({
    mutationFn: (v: { id: string; route: number }) => testChatIntegration(v.id, v.route),
    onSuccess: (r) => toast(r.message, r.ok ? 'info' : 'error'),
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  return (
    <SettingsCard title={t('integrations.chat')} help={t('integrations.chatHelp')}>
      <P.Rows>
        {chats.map((c) => (
          <S.Item key={c.id}>
            <P.Row>
              <P.Grow>
                <MessageSquare size={16} />
                <strong>{c.name}</strong>
                <Badge>{t(`integrations.${c.kind}`)}</Badge>
                {!c.active && <Badge>{t('integrations.off')}</Badge>}
              </P.Grow>
              <IconButton
                label={t('integrations.delete', { name: c.name })}
                onClick={() => remove.mutate(c.id)}
              >
                <Trash2 />
              </IconButton>
            </P.Row>
            <S.Urls>
              <span>{t('integrations.commandUrl')}</span>
              <code>{c.command_url}</code>
              {c.events_url && (
                <>
                  <span>{t('integrations.eventsUrl')}</span>
                  <code>{c.events_url}</code>
                </>
              )}
            </S.Urls>
            {c.notices.map((r, n) => (
              <S.Channel key={n}>
                <code>{r.channel}</code>
                <small>
                  {r.events.length ? r.events.join(', ') : t('integrations.allEvents')}
                  {r.filter.space ? ` · ${r.filter.space}` : ''}
                </small>
                <IconButton
                  label={t('integrations.testChannel', { channel: r.channel })}
                  onClick={() => test.mutate({ id: c.id, route: n })}
                >
                  <Send />
                </IconButton>
              </S.Channel>
            ))}
          </S.Item>
        ))}
      </P.Rows>
      {adding ? (
        <ChatForm
          pending={create.isPending}
          error={create.error ? errorMessage(create.error) : null}
          onCancel={() => setAdding(false)}
          onSave={(body) => create.mutate(body)}
        />
      ) : (
        <Button size="sm" onClick={() => setAdding(true)}>
          <Plus />
          {t('integrations.newChat')}
        </Button>
      )}
    </SettingsCard>
  );
}
