import { Bot } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { uniquePeople, type Peer } from '../../../../editor/presence';
import * as S from './style';

const SHOWN = 5;

function initials(name: string): string {
  const [first = '', second = ''] = name.trim().split(/\s+/);
  return (second ? first.slice(0, 1) + second.slice(0, 1) : first.slice(0, 2)).toUpperCase();
}

/** Who else is in the document: their avatars in their colors, and agents while they write. */
export function Presence({ peers }: { peers: Peer[] }) {
  const { t } = useTranslation();
  const people = uniquePeople(peers);
  if (people.length === 0) return null;
  const agents = people.filter((p) => p.agent);
  const extra = people.length - SHOWN;
  return (
    <S.Wrap>
      {agents.map((agent) => (
        <S.AgentChip key={agent.clientId} $color={agent.color} role="status">
          <Bot aria-hidden size={14} />
          {t('folio.editor.presence.agentWriting', { name: agent.name })}
        </S.AgentChip>
      ))}
      <S.Stack aria-label={t('folio.editor.presence.label', { count: people.length })}>
        {people.slice(0, SHOWN).map((peer) => (
          <S.Face key={peer.clientId} $color={peer.color} title={peer.name}>
            {peer.agent ? <Bot aria-hidden size={14} /> : initials(peer.name)}
            <S.Hidden>{peer.name}</S.Hidden>
          </S.Face>
        ))}
        {extra > 0 && <S.More>+{extra}</S.More>}
      </S.Stack>
    </S.Wrap>
  );
}
