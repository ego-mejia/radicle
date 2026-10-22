import { useTranslation } from 'react-i18next';
import type { Citation } from '../../../../../../services/api/folioChat';
import * as S from './style';

type Props = { question: string; citations: Citation[] };

/** What Radi did to answer, in the names agents see over MCP: one search of the docs and
 * one read per page it cited. */
export function ToolChips({ question, citations }: Props) {
  const { t } = useTranslation();
  const pages = [...new Map(citations.map((c) => [c.node_id, c.title])).values()];
  const short = (text: string, max: number) =>
    text.length > max ? `${text.slice(0, max - 1)}…` : text;
  return (
    <S.Row aria-label={t('folio.radi.tools')}>
      <S.Chip>search_docs · “{short(question, 28)}”</S.Chip>
      {pages.map((title) => (
        <S.Chip key={title}>get_page · {short(title, 26)}</S.Chip>
      ))}
    </S.Row>
  );
}
