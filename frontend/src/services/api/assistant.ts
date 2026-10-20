import { api, unwrap } from './client';
import type { components } from './schema';

export type ChatMessage = { role: 'user' | 'assistant'; content: string };
export type ChatReply = components['schemas']['ChatOut'];

/** Ask Radi; send the recent conversation so follow-ups make sense. */
export async function askRadi(messages: ChatMessage[], language: string): Promise<ChatReply> {
  return unwrap(
    await api.POST('/api/v1/assistant/chat', {
      body: { messages: messages.slice(-12), language: language.startsWith('es') ? 'es' : 'en' },
    }),
  );
}
