import { SquareCheckBig } from 'lucide-react';
import { useContext } from 'react';
import { useTranslation } from 'react-i18next';
import { IconButton } from '../../../../../../components/ui/Button';
import { formatDate, isOverdue } from '../../../../../../lib/format';
import { DocActions } from '../../actions';
import { type DocNode, plainText } from '../../anchors';
import { Inline } from '../Inline';
import * as S from './style';

/** An action item as the reader sees it: checked or not, who it's for and when, and a
 * button to make it a Docket ticket where the page allows it. */
export function ActionItem({ node }: { node: DocNode }) {
  const { t } = useTranslation();
  const { onTicket } = useContext(DocActions);
  const a = node.attrs ?? {};
  const done = Boolean(a.done);
  const due = a.due ? String(a.due) : null;
  return (
    <S.Item $done={done}>
      <input type="checkbox" checked={done} readOnly aria-label={t('folio.reader.actionItem')} />
      <S.Text>
        <Inline nodes={node.content} />
      </S.Text>
      {a.assignee ? <S.Who>@{String(a.assignee)}</S.Who> : null}
      {due && (
        <S.When $late={!done && isOverdue(due)} title={t('folio.reader.due')}>
          {formatDate(due)}
        </S.When>
      )}
      {onTicket ? (
        <IconButton
          label={t('folio.tickets.createFromItem')}
          onClick={(e) => onTicket(plainText(node.content), e.currentTarget)}
        >
          <SquareCheckBig />
        </IconButton>
      ) : null}
    </S.Item>
  );
}
