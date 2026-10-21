import { readEvents } from '../../lib/sse';
import { ApiError, CSRF_COOKIE, api, readCookie, unwrap, type Problem } from './client';
import type { components } from './schema';

type S = components['schemas'];
export type ChatAvailability = S['ChatAvailabilityOut'];
export type ChatSession = S['ChatSessionOut'];
export type ChatSessionDetail = S['ChatSessionDetailOut'];
export type ChatMessage = S['ChatMessageOut'];
export type Citation = S['CitationOut'];
export type ChatQuestion = S['ChatQuestionIn'];
export type Unanswered = S['UnansweredOut'];

/** Query keys for the docs chat (Folio 4.5). */
export const chatKeys = {
  availability: ['folio', 'chat', 'availability'] as const,
  sessions: ['folio', 'chat', 'sessions'] as const,
  session: (id: string) => ['folio', 'chat', 'session', id] as const,
  unanswered: ['folio', 'chat', 'unanswered'] as const,
};

export async function fetchChatAvailability(): Promise<ChatAvailability> {
  return unwrap(await api.GET('/api/v1/folio/chat/availability'));
}

export async function fetchChatSessions(): Promise<ChatSession[]> {
  return unwrap(await api.GET('/api/v1/folio/chat/sessions')).items;
}

export async function createChatSession(): Promise<ChatSession> {
  return unwrap(await api.POST('/api/v1/folio/chat/sessions', { body: {} }));
}

export async function fetchChatSession(id: string): Promise<ChatSessionDetail> {
  return unwrap(
    await api.GET('/api/v1/folio/chat/sessions/{session_id}', {
      params: { path: { session_id: id } },
    }),
  );
}

export async function sendChatFeedback(
  messageId: string,
  value: 'up' | 'down',
  note?: string,
): Promise<ChatMessage> {
  return unwrap(
    await api.POST('/api/v1/folio/chat/messages/{message_id}/feedback', {
      params: { path: { message_id: messageId } },
      body: { value, note: note || null },
    }),
  );
}

export async function fetchUnanswered(): Promise<Unanswered[]> {
  return unwrap(await api.GET('/api/v1/folio/admin/chat/unanswered')).items;
}

async function problemOf(response: Response): Promise<Problem> {
  const fallback: Problem = {
    type: 'about:blank',
    title: response.statusText,
    status: response.status,
    detail: response.statusText || 'Request failed',
    errors: [],
  };
  try {
    return { ...fallback, ...((await response.json()) as Partial<Problem>) };
  } catch {
    return fallback;
  }
}

/**
 * Asks the docs in a session. `onText` gets the answer as it is written; the promise
 * resolves with the saved message and its citations.
 */
export async function askDocs(
  sessionId: string,
  question: ChatQuestion,
  onText: (piece: string) => void,
  signal?: AbortSignal,
): Promise<ChatMessage> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const token = readCookie(CSRF_COOKIE);
  if (token) headers['X-CSRF-Token'] = token;
  const response = await globalThis.fetch(
    `${window.location.origin}/api/v1/folio/chat/sessions/${sessionId}/messages`,
    { method: 'POST', credentials: 'same-origin', headers, body: JSON.stringify(question), signal },
  );
  if (!response.ok || !response.body) throw new ApiError(await problemOf(response));
  for await (const { event, data } of readEvents(response.body)) {
    const payload = data as { text?: string; message?: ChatMessage; detail?: string };
    if (event === 'delta' && payload.text) onText(payload.text);
    if (event === 'done' && payload.message) return payload.message;
    if (event === 'error') {
      const detail = payload.detail ?? 'The AI provider failed.';
      throw new ApiError({ type: 'about:blank', title: 'AI', status: 502, detail, errors: [] });
    }
  }
  throw new ApiError({
    type: 'about:blank',
    title: 'AI',
    status: 502,
    detail: 'The answer stopped before it ended. Try again.',
    errors: [],
  });
}
