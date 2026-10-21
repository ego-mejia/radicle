import { useMutation } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { AlertTriangle, ThumbsDown, ThumbsUp } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MarkdownView } from '../../../../../../components/Markdown/MarkdownView';
import { Button, IconButton } from '../../../../../../components/ui/Button';
import { type ChatMessage, sendChatFeedback } from '../../../../../../services/api/folioChat';
import { linkCitations, pageOf } from '../../citations';
import * as S from './style';

type Props = { message: ChatMessage };

/** One answer: its text with linked citations, the sources it used, and thumbs. */
export function ChatAnswer({ message }: Props) {
  const { t } = useTranslation();
  const [feedback, setFeedback] = useState(message.feedback);
  const [noting, setNoting] = useState(false);
  const [note, setNote] = useState('');
  const rate = useMutation({
    mutationFn: (v: { value: 'up' | 'down'; note?: string }) =>
      sendChatFeedback(message.id, v.value, v.note),
    onSuccess: (saved) => setFeedback(saved.feedback),
  });
  const outdated = message.citations.some((c) => c.outdated);

  return (
    <S.Answer>
      <MarkdownView>{linkCitations(message.content, message.citations)}</MarkdownView>
      {outdated && (
        <S.Warning role="note">
          <AlertTriangle aria-hidden />
          {t('folio.chat.outdated')}
        </S.Warning>
      )}
      {message.citations.length > 0 && (
        <S.Sources aria-label={t('folio.chat.sources')}>
          {message.citations.map((c) => (
            <S.Source key={c.n} $outdated={c.outdated}>
              <Link
                to="/folio/p/$page"
                params={{ page: pageOf(c.url) }}
                hash={c.anchor ?? undefined}
              >
                <S.N>{c.n}</S.N>
                <span>
                  {c.title}
                  {c.section && <S.Section> › {c.section}</S.Section>}
                </span>
              </Link>
            </S.Source>
          ))}
        </S.Sources>
      )}
      <S.Feedback>
        <IconButton
          label={t('folio.chat.helpful')}
          active={feedback === 'up'}
          onClick={() => rate.mutate({ value: 'up' })}
        >
          <ThumbsUp aria-hidden />
        </IconButton>
        <IconButton
          label={t('folio.chat.notHelpful')}
          active={feedback === 'down'}
          onClick={() => setNoting(true)}
        >
          <ThumbsDown aria-hidden />
        </IconButton>
      </S.Feedback>
      {noting && (
        <S.Note
          onSubmit={(e) => {
            e.preventDefault();
            rate.mutate({ value: 'down', note });
            setNoting(false);
          }}
        >
          <S.NoteInput
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={t('folio.chat.notePlaceholder')}
            aria-label={t('folio.chat.note')}
            maxLength={1000}
          />
          <Button type="submit" size="sm">
            {t('folio.chat.sendNote')}
          </Button>
        </S.Note>
      )}
    </S.Answer>
  );
}
