import { useQuery } from '@tanstack/react-query';
import { ThumbsDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { SettingsCard } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { formatDateTime } from '../../../../lib/format';
import { chatKeys, fetchUnanswered } from '../../../../services/api/folioChat';
import * as S from './style';

/** Folio, Admin, Chat (Folio 4.5): questions the docs didn't answer, or whose answer got a
 * thumbs down, to know what to document next. */
export function UnansweredQuestions() {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const { data, isPending, error } = useQuery({
    queryKey: chatKeys.unanswered,
    queryFn: fetchUnanswered,
  });

  return (
    <SettingsCard title={t('folio.chat.unanswered.title')} help={t('folio.chat.unanswered.help')}>
      {isPending ? (
        <PageSpinner />
      ) : error ? (
        <S.Muted role="alert">{errorMessage(error)}</S.Muted>
      ) : data.length === 0 ? (
        <S.Muted>{t('folio.chat.unanswered.empty')}</S.Muted>
      ) : (
        <S.List>
          {data.map((q, i) => (
            <S.Item key={i}>
              <S.Question>{q.question}</S.Question>
              <S.Meta>
                <time dateTime={q.asked_at}>{formatDateTime(q.asked_at)}</time>
                {q.feedback === 'down' ? (
                  <S.Down>
                    <ThumbsDown aria-hidden />
                    {t('folio.chat.unanswered.down')}
                  </S.Down>
                ) : (
                  <span>{t('folio.chat.unanswered.noSource')}</span>
                )}
              </S.Meta>
              {q.feedback_note && <S.Note>“{q.feedback_note}”</S.Note>}
            </S.Item>
          ))}
        </S.List>
      )}
    </SettingsCard>
  );
}
