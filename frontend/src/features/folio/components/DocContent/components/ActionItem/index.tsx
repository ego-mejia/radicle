import { useTranslation } from 'react-i18next';
import { formatDate, isOverdue } from '../../../../../../lib/format';
import type { DocNode } from '../../anchors';
import { Inline } from '../Inline';
import * as S from './style';

/** An action item as the reader sees it: checked or not, who it's for and when. */
export function ActionItem({ node }: { node: DocNode }) {
  const { t } = useTranslation();
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
    </S.Item>
  );
}
