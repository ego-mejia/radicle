import { useMutation } from '@tanstack/react-query';
import { Send, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MarkdownView } from '../../../../components/Markdown/MarkdownView';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { askRadi, type ChatMessage } from '../../../../services/api/assistant';
import type { RadiMood } from '../Radi';
import * as S from './style';

type Line = ChatMessage & { notice?: string | null };
type Props = { onClose: () => void; onMood: (mood: RadiMood) => void };

const SUGGESTIONS = ['project', 'people', 'board', 'agent'] as const;

/** The help chat that opens out of Radi. */
export function RadiChat({ onClose, onMood }: Props) {
  const { t, i18n } = useTranslation();
  const errorMessage = useErrorMessage();
  const [lines, setLines] = useState<Line[]>([]);
  const [draft, setDraft] = useState('');
  const input = useRef<HTMLTextAreaElement>(null);
  const end = useRef<HTMLDivElement>(null);
  const ask = useMutation({
    mutationFn: (history: ChatMessage[]) => askRadi(history, i18n.language),
    onMutate: () => onMood('thinking'),
    onSuccess: (reply) => {
      setLines((prev) => [
        ...prev,
        { role: 'assistant', content: reply.answer, notice: reply.notice },
      ]);
      onMood('answered');
    },
    onError: (error) => {
      setLines((prev) => [...prev, { role: 'assistant', content: errorMessage(error) }]);
      onMood('listening');
    },
  });

  useEffect(() => {
    input.current?.focus();
  }, []);
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: 'end' });
  }, [lines, ask.isPending]);

  const send = (text: string) => {
    const question = text.trim();
    if (!question || ask.isPending) return;
    const history = [...lines, { role: 'user' as const, content: question }];
    setLines(history);
    setDraft('');
    ask.mutate(history.map(({ role, content }) => ({ role, content })));
  };

  return (
    <S.Panel
      role="dialog"
      aria-label={t('assistant.title')}
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
    >
      <S.Head>
        <div>
          <strong>Radi</strong>
          <small>{t('assistant.subtitle')}</small>
        </div>
        <S.Close type="button" aria-label={t('assistant.close')} onClick={onClose}>
          <X size={16} />
        </S.Close>
      </S.Head>
      <S.Messages aria-live="polite">
        <S.Bubble $mine={false}>{t('assistant.greeting')}</S.Bubble>
        {lines.length === 0 && (
          <S.Suggestions>
            {SUGGESTIONS.map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => send(t(`assistant.suggestions.${key}`))}
              >
                {t(`assistant.suggestions.${key}`)}
              </button>
            ))}
          </S.Suggestions>
        )}
        {lines.map((line, i) =>
          line.role === 'user' ? (
            <S.Bubble key={i} $mine>
              {line.content}
            </S.Bubble>
          ) : (
            <S.Bubble key={i} $mine={false}>
              <MarkdownView readOnly>{line.content}</MarkdownView>
              {line.notice && <S.Notice>{line.notice}</S.Notice>}
            </S.Bubble>
          ),
        )}
        {ask.isPending && <S.Typing>{t('assistant.thinking')}</S.Typing>}
        <div ref={end} />
      </S.Messages>
      <S.Composer
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
      >
        <textarea
          ref={input}
          rows={2}
          value={draft}
          aria-label={t('assistant.ask')}
          placeholder={t('assistant.placeholder')}
          maxLength={4000}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              send(draft);
            }
          }}
        />
        <S.Send
          type="submit"
          aria-label={t('assistant.send')}
          disabled={!draft.trim() || ask.isPending}
        >
          <Send size={16} />
        </S.Send>
      </S.Composer>
    </S.Panel>
  );
}
