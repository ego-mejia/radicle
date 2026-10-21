import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Send } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MarkdownView } from '../../../../components/Markdown/MarkdownView';
import { IconButton } from '../../../../components/ui/Button';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import {
  askDocs,
  type ChatMessage,
  chatKeys,
  createChatSession,
} from '../../../../services/api/folioChat';
import { ChatAnswer } from './components/ChatAnswer';
import * as S from './style';

type Line =
  | { kind: 'question'; text: string }
  | { kind: 'answer'; message: ChatMessage }
  | { kind: 'error'; text: string };

type Props = {
  /** Smaller, for the home's chat block. */
  compact?: boolean;
  /** Only docs in this space. */
  space?: string;
  autoFocus?: boolean;
};

/** Ask the docs (Folio 4.5): answers written only from the docs you can see, with sources. */
export function DocsChat({ compact = false, space, autoFocus = false }: Props) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [session, setSession] = useState<string | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [draft, setDraft] = useState('');
  const [partial, setPartial] = useState('');
  const input = useRef<HTMLTextAreaElement>(null);
  const end = useRef<HTMLDivElement>(null);

  const ask = useMutation({
    mutationFn: async (question: string) => {
      const id = session ?? (await createChatSession()).id;
      setSession(id);
      return askDocs(id, { content: question, space: space ?? null }, (piece) =>
        setPartial((p) => p + piece),
      );
    },
    onSuccess: (message) => {
      setLines((prev) => [...prev, { kind: 'answer', message }]);
      void queryClient.invalidateQueries({ queryKey: chatKeys.sessions });
    },
    onError: (error) => setLines((prev) => [...prev, { kind: 'error', text: errorMessage(error) }]),
    onSettled: () => setPartial(''),
  });

  useEffect(() => {
    if (autoFocus) input.current?.focus();
  }, [autoFocus]);
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: 'end' });
  }, [lines, partial]);

  const send = () => {
    const question = draft.trim();
    if (!question || ask.isPending) return;
    setLines((prev) => [...prev, { kind: 'question', text: question }]);
    setDraft('');
    ask.mutate(question);
  };

  return (
    <S.Chat $compact={compact}>
      <S.Lines aria-live="polite">
        {lines.length === 0 && !ask.isPending && <S.Hint>{t('folio.chat.hint')}</S.Hint>}
        {lines.map((line, i) =>
          line.kind === 'question' ? (
            <S.Question key={i}>{line.text}</S.Question>
          ) : line.kind === 'answer' ? (
            <ChatAnswer key={i} message={line.message} />
          ) : (
            <S.Error key={i} role="alert">
              {line.text}
            </S.Error>
          ),
        )}
        {ask.isPending &&
          (partial ? (
            <MarkdownView>{partial}</MarkdownView>
          ) : (
            <S.Thinking>{t('folio.chat.thinking')}</S.Thinking>
          ))}
        <div ref={end} />
      </S.Lines>
      <S.Compose
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <S.Input
          ref={input}
          value={draft}
          rows={compact ? 1 : 2}
          maxLength={2000}
          placeholder={t('folio.chat.placeholder')}
          aria-label={t('folio.chat.question')}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <IconButton type="submit" label={t('folio.chat.send')} disabled={ask.isPending}>
          <Send aria-hidden />
        </IconButton>
      </S.Compose>
    </S.Chat>
  );
}
