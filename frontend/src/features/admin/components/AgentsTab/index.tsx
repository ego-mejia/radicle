import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bot, KeyRound, Plus, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Avatar } from '../../../../components/ui/Avatar';
import { Badge } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { SettingsCard, SettingsParts as S } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  adminKeys,
  createAgent,
  createAgentToken,
  fetchUsers,
  fetchUserTokens,
  patchUser,
  revokeUserToken,
} from '../../../../services/api/admin';
import { mcpSummary } from '../../../../lib/mcp';
import type { User } from '../../../../services/api/types';
import { McpPermissionsModal } from '../McpPermissionsModal';
import { NewUserModal } from '../NewUserModal';
import { TokenList } from '../TokenList';
import { TokenReveal } from '../TokenReveal';

type Reveal = { handle: string; token: string; mcpUrl: string };

function AgentTokens({ handle, onReveal }: { handle: string; onReveal: (r: Reveal) => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const { data: tokens = [] } = useQuery({
    queryKey: adminKeys.tokens(handle),
    queryFn: () => fetchUserTokens(handle),
  });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: adminKeys.tokens(handle) });
  const revoke = useMutation({
    mutationFn: (id: string) => revokeUserToken(handle, id),
    onSuccess: refresh,
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const create = useMutation({
    mutationFn: () => createAgentToken(handle, `token ${new Date().toISOString().slice(0, 10)}`),
    onSuccess: (token) => {
      refresh();
      onReveal({ handle, token: token.token, mcpUrl: `${window.location.origin}/mcp` });
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  return (
    <>
      <TokenList tokens={tokens} onRevoke={(id) => revoke.mutate(id)} />
      <S.Actions>
        <Button size="sm" onClick={() => create.mutate()}>
          <KeyRound />
          {t('admin.newToken')}
        </Button>
      </S.Actions>
    </>
  );
}

export function AgentsTab() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [creating, setCreating] = useState(false);
  const [reveal, setReveal] = useState<Reveal | null>(null);
  const [editing, setEditing] = useState<User | null>(null);
  const { data: users, isPending } = useQuery({ queryKey: adminKeys.users, queryFn: fetchUsers });
  const toggle = useMutation({
    mutationFn: (v: { handle: string; active: boolean }) =>
      patchUser(v.handle, { is_active: v.active }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: adminKeys.users }),
    onError: (e) => toast(errorMessage(e), 'error'),
  });

  if (isPending) return <PageSpinner />;
  const agents = (users ?? []).filter((u) => u.kind === 'agent');

  return (
    <>
      {reveal && (
        <TokenReveal token={reveal.token} mcpUrl={reveal.mcpUrl} onClose={() => setReveal(null)} />
      )}
      {agents.map((agent) => (
        <SettingsCard key={agent.handle} title={agent.display_name}>
          <S.Row>
            <S.Grow>
              <Avatar handle={agent.handle} kind="agent" size={26} />
              <small>@{agent.handle}</small>
              {!agent.is_active && <Badge tone="danger">{t('admin.inactive')}</Badge>}
            </S.Grow>
            <Button
              size="sm"
              variant={agent.is_active ? 'danger' : 'secondary'}
              onClick={() => toggle.mutate({ handle: agent.handle, active: !agent.is_active })}
            >
              {agent.is_active ? t('admin.deactivate') : t('admin.activate')}
            </Button>
          </S.Row>
          <S.Row>
            <S.Grow>
              <ShieldCheck size={16} />
              {mcpSummary(t, agent)}
            </S.Grow>
            <Button size="sm" onClick={() => setEditing(agent)}>
              {t('admin.mcp.title')}
            </Button>
          </S.Row>
          <AgentTokens handle={agent.handle} onReveal={setReveal} />
        </SettingsCard>
      ))}
      {agents.length === 0 && (
        <SettingsCard title={t('admin.agents')} help={t('admin.agentsHelp')}>
          <S.Grow>
            <Bot size={18} />
            {t('admin.noAgents')}
          </S.Grow>
        </SettingsCard>
      )}
      <S.Actions>
        <Button variant="primary" onClick={() => setCreating(true)}>
          <Plus />
          {t('admin.newAgent')}
        </Button>
      </S.Actions>
      {editing && <McpPermissionsModal agent={editing} onClose={() => setEditing(null)} />}
      {creating && (
        <NewUserModal
          kind="agent"
          onClose={() => setCreating(false)}
          onCreate={async (person) => {
            const created = await createAgent({
              handle: person.handle,
              display_name: person.display_name,
              mcp_tools: person.mcp_tools,
            });
            await queryClient.invalidateQueries({ queryKey: adminKeys.users });
            setReveal({
              handle: created.agent.handle,
              token: created.token.token,
              mcpUrl: created.mcp_url,
            });
          }}
        />
      )}
    </>
  );
}
