import { createLink } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import type { FolioCard } from '../../../../../../services/api/folio';
import { cardMeta, kindLabel, pageParams } from '../../meta';
import { StatusBadge } from '../../../../components/StatusBadge';
import * as S from './style';

const ItemLink = createLink(S.Item);

type Props = { title: string; docs: FolioCard[]; numbered?: boolean };

/** A block of docs: the latest posts, or the most read with their rank. */
export function DocList({ title, docs, numbered = false }: Props) {
  const { t } = useTranslation();
  return (
    <S.Section aria-label={title}>
      <S.Heading>{title}</S.Heading>
      {docs.length === 0 ? (
        <S.Empty>{t('folio.home.nothingYet')}</S.Empty>
      ) : (
        <S.List>
          {docs.map((doc, i) => (
            <li key={doc.id}>
              <ItemLink to="/folio/p/$page" params={pageParams(doc)}>
                {numbered && <S.Number>{String(i + 1).padStart(2, '0')}</S.Number>}
                <S.Text>
                  {!numbered && <S.Kind>{kindLabel(t, doc)}</S.Kind>}
                  <S.Title>
                    {doc.title} <StatusBadge status={doc.status} />
                  </S.Title>
                  <S.Meta>{numbered ? doc.space_name : cardMeta(t, doc, true)}</S.Meta>
                </S.Text>
              </ItemLink>
            </li>
          ))}
        </S.List>
      )}
    </S.Section>
  );
}
