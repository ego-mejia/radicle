import { ChatCard } from './components/ChatCard';
import { WebhooksCard } from './components/WebhooksCard';
import * as S from './style';

/** Admin, Integrations: what leaves Radicle (ADR 0042). Shared by every app. */
export function IntegrationsTab() {
  return (
    <S.Stack>
      <ChatCard />
      <WebhooksCard />
    </S.Stack>
  );
}
