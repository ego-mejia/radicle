import { ChatCard } from './components/ChatCard';
import { RulesCard } from './components/RulesCard';
import { WebhooksCard } from './components/WebhooksCard';
import * as S from './style';

/** Admin, Integrations: what leaves Radicle (ADR 0042). Shared by every app. */
export function IntegrationsTab() {
  return (
    <S.Stack>
      <ChatCard />
      <WebhooksCard />
      <RulesCard />
    </S.Stack>
  );
}
