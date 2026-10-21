import { createLink } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { Avatar } from '../../../../../../components/ui/Avatar';
import { assetUrl, type FolioCard } from '../../../../../../services/api/folio';
import { cardMeta, kindLabel, pageParams } from '../../meta';
import { RootsArt } from '../../../../components/RootsArt';
import * as S from './style';

const CardLink = createLink(S.Card);

/** The bento's big card: the featured doc with its cover. */
export function Featured({ doc }: { doc: FolioCard }) {
  const { t } = useTranslation();
  return (
    <CardLink to="/folio/p/$page" params={pageParams(doc)} aria-label={doc.title}>
      <S.Cover>
        {doc.cover_asset_id ? <img src={assetUrl(doc.cover_asset_id)} alt="" /> : <RootsArt />}
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
