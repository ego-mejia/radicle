import { useMutation } from '@tanstack/react-query';
import { MousePointer2, Send, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MarkdownView } from '../../../../components/Markdown/MarkdownView';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { askRadi, type ChatMessage } from '../../../../services/api/assistant';
import type { TourStep } from '../../lib/tour';
import type { RadiMood } from '../Radi';
import * as S from './style';

type Line = ChatMessage & { notice?: string | null; tour?: TourStep[] };
type Props = {
  onClose: () => void;
  onMood: (mood: RadiMood) => void;
  /** Start a tour; Radi's own tours (from the LLM) start right away. */
  onTour: (steps: TourStep[]) => void;
  /** Kept by the parent so the conversation survives a tour. */
  lines: Line[];
  setLines: React.Dispatch<React.SetStateAction<Line[]>>;
};
export type { Line as ChatLine };

const SUGGESTIONS = ['project', 'people', 'board', 'agent'] as const;

/** The help chat that opens out of Radi. */
export function RadiChat({ onClose, onMood, onTour, lines, setLines }: Props) {
  const { t, i18n } = useTranslation();
  const errorMessage = useErrorMessage();
  const [draft, setDraft] = useState('');
  const input = useRef<HTMLTextAreaElement>(null);
  const end = useRef<HTMLDivElement>(null);
  const ask = useMutation({
    mutationFn: (history: ChatMessage[]) => askRadi(history, i18n.language),
    onMutate: () => onMood('thinking'),
    onSuccess: (reply) => {
      setLines((prev) => [
        ...prev,
        { role: 'assistant', content: reply.answer, notice: reply.notice, tour: reply.tour },
      ]);
      onMood('answered');
      if (reply.autoplay && reply.tour.length) onTour(reply.tour);
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

  const suggestions = (
    <S.Suggestions>
      {SUGGESTIONS.map((key) => (
        <button key={key} type="button" onClick={() => send(t(`assistant.suggestions.${key}`))}>
          {t(`assistant.suggestions.${key}`)}
        </button>
      ))}
    </S.Suggestions>
  );

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
              {line.tour && line.tour.length > 0 && (
                <S.ShowMe type="button" onClick={() => onTour(line.tour!)}>
                  <MousePointer2 size={14} />
                  {t('assistant.tour.showMe')}
                </S.ShowMe>
              )}
            </S.Bubble>
          ),
        )}
        {ask.isPending && <S.Typing>{t('assistant.thinking')}</S.Typing>}
        {lines.length > 0 && !ask.isPending && (
          <>
            <S.Hint>{t('assistant.more')}</S.Hint>
            {suggestions}
          </>
        )}
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
