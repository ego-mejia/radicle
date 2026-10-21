import { createLink } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import type { FolioCard } from '../../../../../../services/api/folio';
import { pageParams } from '../../meta';
import * as S from './style';

const MoreLink = createLink(S.More);

type Props = { doc: FolioCard; label: string; tone: S.Tone };

/** A side card of the bento: the announcement (accent) or AI Tools (plain). */
export function Spotlight({ doc, label, tone }: Props) {
  const { t } = useTranslation();
  return (
    <S.Card $tone={tone} aria-label={label}>
      <S.Label $tone={tone}>{label}</S.Label>
      <S.Title>{doc.title}</S.Title>
      {doc.description && <S.Text>{doc.description}</S.Text>}
      <MoreLink
        to="/folio/p/$page"
        params={pageParams(doc)}
        aria-label={t('folio.home.readDoc', { title: doc.title })}
      >
        {t('folio.home.read')}
      </MoreLink>
    </S.Card>
  );
}
