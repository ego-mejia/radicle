import { useQuery } from '@tanstack/react-query';
import { ExternalLink } from 'lucide-react';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchLinkPreview, folioKeys, type FolioLinkPreview } from '../../../../services/api/folio';
import * as S from './style';

type Props = {
  url: string;
  /** The title saved in the document, shown while the preview loads or if it fails. */
  title?: string | null;
  /** Called once the preview arrives, so the editor can keep its title and provider. */
  onPreview?: (preview: FolioLinkPreview) => void;
};

/** A pasted link: an interactive embed for YouTube, Figma, Loom, Google Docs and GitHub
 * gists, a card with the page's title, description and image for everything else. */
export function EmbedCard({ url, title, onPreview }: Props) {
  const { t } = useTranslation();
  const { data } = useQuery({
    queryKey: folioKeys.linkPreview(url),
    queryFn: () => fetchLinkPreview(url),
    staleTime: 60 * 60 * 1000,
    retry: false,
  });
  useEffect(() => {
    if (data) onPreview?.(data);
    // Only when a new preview arrives.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  if (data?.embed_url) {
    return (
      <S.Frame>
        <iframe
          src={data.embed_url}
          title={data.title || title || url}
          loading="lazy"
          referrerPolicy="strict-origin-when-cross-origin"
          // Cross-origin, so allow-same-origin only gives the embed its own origin back.
          sandbox="allow-scripts allow-same-origin allow-popups allow-presentation allow-forms"
          allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
          allowFullScreen
        />
      </S.Frame>
    );
  }
  return (
    <S.Card href={url} target="_blank" rel="noreferrer noopener">
      <S.Text>
        <S.Title>{data?.title || title || url}</S.Title>
        {data?.description && <S.Description>{data.description}</S.Description>}
        <S.Site>
          {data?.icon_url && <img src={data.icon_url} alt="" width={14} height={14} />}
          {data?.site_name || new URL(url).hostname}
          <ExternalLink aria-hidden size={12} />
          <S.Hidden>{t('folio.embed.opensNewTab')}</S.Hidden>
        </S.Site>
      </S.Text>
      {data?.image_url && <S.Image src={data.image_url} alt="" loading="lazy" />}
    </S.Card>
  );
}
