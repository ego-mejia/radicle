import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { fetchReactions, setReaction, socialKeys } from '../../../../services/api/folioSocial';
import { REACTIONS } from '../PageSocial';
import * as S from './style';

/** Reactions under a comment: the ones someone used, plus a quick 👍. */
export function CommentReactions({ commentId }: { commentId: string }) {
  const { t } = useTranslation();
  const client = useQueryClient();
  const key = socialKeys.reactions('comment', commentId);
  const { data = [] } = useQuery({
    queryKey: key,
    queryFn: () => fetchReactions('comment', commentId),
  });
  const react = useMutation({
    mutationFn: ({ emoji, on }: { emoji: string; on: boolean }) =>
      setReaction('comment', commentId, emoji, on),
    onSuccess: (next) => client.setQueryData(key, next),
  });
  const used = new Map(data.map((r) => [r.emoji, r]));
  const shown = REACTIONS.filter((e) => used.has(e) || e === '👍');
  return (
    <S.Reactions role="group" aria-label={t('folio.social.reactions')}>
      {shown.map((emoji) => {
        const r = used.get(emoji);
        return (
          <S.Reaction
            key={emoji}
            type="button"
            $mine={!!r?.mine}
            aria-pressed={!!r?.mine}
            aria-label={t('folio.social.react', { emoji, count: r?.count ?? 0 })}
            onClick={() => react.mutate({ emoji, on: !r?.mine })}
          >
            <span aria-hidden>{emoji}</span>
            {r && <span>{r.count}</span>}
          </S.Reaction>
        );
      })}
    </S.Reactions>
  );
}
