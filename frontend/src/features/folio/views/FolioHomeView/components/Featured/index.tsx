import { createLink } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { Avatar } from '../../../../../../components/ui/Avatar';
import { assetUrl, type FolioCard } from '../../../../../../services/api/folio';
import { cardMeta, kindLabel, pageParams } from '../../meta';
import * as S from './style';

const CardLink = createLink(S.Card);

/** Radicle's roots, drawn in the accent color over the dark cover. */
function Roots() {
  return (
    <svg viewBox="0 0 720 260" preserveAspectRatio="xMidYMid slice" aria-hidden>
      <g fill="none" stroke="currentColor" strokeLinecap="round">
        <path d="M360 40 C360 110 300 130 250 170 S170 240 120 260" strokeWidth="2.5" />
        <path d="M360 40 C365 120 420 140 470 175 S560 230 620 260" strokeWidth="2" opacity="0.7" />
        <path d="M300 125 C290 170 300 210 330 260" strokeWidth="1.5" opacity="0.5" />
        <path d="M430 140 C470 120 520 120 560 140" strokeWidth="1.5" opacity="0.5" />
      </g>
      <g fill="currentColor">
        <ellipse cx="360" cy="34" rx="26" ry="20" />
        <circle cx="250" cy="170" r="5" />
        <circle cx="470" cy="175" r="5" />
        <circle cx="560" cy="140" r="4" />
      </g>
    </svg>
  );
}

/** The bento's big card: the featured doc with its cover. */
export function Featured({ doc }: { doc: FolioCard }) {
  const { t } = useTranslation();
  return (
    <CardLink to="/folio/p/$page" params={pageParams(doc)} aria-label={doc.title}>
      <S.Cover>
        {doc.cover_asset_id ? <img src={assetUrl(doc.cover_asset_id)} alt="" /> : <Roots />}
      </S.Cover>
      <S.Body>
        <S.Tag>{kindLabel(t, doc)}</S.Tag>
        <S.Title>{doc.title}</S.Title>
        {doc.description && <S.Description>{doc.description}</S.Description>}
        <S.Meta>
          {doc.author && (
            <Avatar handle={doc.author} name={doc.author_name ?? undefined} size={28} />
          )}
          {cardMeta(t, doc)}
        </S.Meta>
      </S.Body>
    </CardLink>
  );
}
