import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Bell, BellOff, Share2, Star } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  fetchFavorites,
  fetchReactions,
  fetchWatching,
  setFavorite,
  setReaction,
  setWatching,
  socialKeys,
} from '../../../../services/api/folioSocial';
import { ShareDialog } from '../ShareDialog';
import * as S from './style';

export const REACTIONS = ['👍', '❤️', '🎉', '👀', '🚀', '✅'] as const;

/** Reactions, Follow, the favorite star and Share under a page's byline. */
export function PageSocial({ nodeId, title = '' }: { nodeId: string; title?: string }) {
  const { t } = useTranslation();
  const [sharing, setSharing] = useState(false);
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const client = useQueryClient();
  const onError = (e: unknown) => toast(errorMessage(e), 'error');

  const reactions = useQuery({
    queryKey: socialKeys.reactions('node', nodeId),
    queryFn: () => fetchReactions('node', nodeId),
  });
  const watching = useQuery({
    queryKey: socialKeys.watch('node', nodeId),
    queryFn: () => fetchWatching('node', nodeId),
  });
  const favorites = useQuery({ queryKey: socialKeys.favorites, queryFn: fetchFavorites });
  const starred = favorites.data?.nodes.some((n) => n.id === nodeId) ?? false;

  const react = useMutation({
    mutationFn: ({ emoji, on }: { emoji: string; on: boolean }) =>
      setReaction('node', nodeId, emoji, on),
    onSuccess: (data) => client.setQueryData(socialKeys.reactions('node', nodeId), data),
    onError,
  });
  const watch = useMutation({
    mutationFn: (on: boolean) => setWatching('node', nodeId, on),
    onSuccess: (_, on) => client.setQueryData(socialKeys.watch('node', nodeId), on),
    onError,
  });
  const star = useMutation({
    mutationFn: (on: boolean) => setFavorite('node', nodeId, on),
    onSuccess: () => client.invalidateQueries({ queryKey: socialKeys.favorites }),
    onError,
  });

  const counts = new Map((reactions.data ?? []).map((r) => [r.emoji, r]));
  return (
    <S.Bar aria-label={t('folio.social.label')}>
      <S.Reactions role="group" aria-label={t('folio.social.reactions')}>
        {REACTIONS.map((emoji) => {
          const r = counts.get(emoji);
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
              {r && <S.Count>{r.count}</S.Count>}
            </S.Reaction>
          );
        })}
      </S.Reactions>
      <S.Toggles>
        <S.Toggle
          type="button"
          aria-pressed={!!watching.data}
          onClick={() => watch.mutate(!watching.data)}
        >
          {watching.data ? <BellOff aria-hidden /> : <Bell aria-hidden />}
          {watching.data ? t('folio.social.unwatch') : t('folio.social.watch')}
        </S.Toggle>
        <S.Toggle
          type="button"
          aria-pressed={starred}
          $on={starred}
          onClick={() => star.mutate(!starred)}
        >
          <Star aria-hidden />
          {starred ? t('folio.social.unfavorite') : t('folio.social.favorite')}
        </S.Toggle>
        <S.Toggle type="button" onClick={() => setSharing(true)}>
          <Share2 aria-hidden />
          {t('folio.share.button')}
        </S.Toggle>
      </S.Toggles>
      <ShareDialog nodeId={nodeId} title={title} open={sharing} onOpenChange={setSharing} />
    </S.Bar>
  );
}
