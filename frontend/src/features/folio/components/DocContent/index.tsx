import { Fragment, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { type DocNode, headingsOf } from './anchors';
import { ActionItem } from './components/ActionItem';
import { Inline } from './components/Inline';
import { type ChildPage, RichBlock } from './components/RichBlock';
import * as S from './style';

type Props = {
  doc: DocNode | null | undefined;
  /** Pages under this one, for the child pages block. */
  childPages?: ChildPage[];
  size?: 'regular' | 'large';
};

/** A published or draft Folio document (TipTap JSON), read-only. */
export function DocContent({ doc, childPages = [], size = 'regular' }: Props) {
  const { t } = useTranslation();
  const headings = headingsOf(doc);
  let next = 0;

  const stack = (nodes: DocNode[] = []) => (
    <S.Flow>
      {nodes.map((n, i) => (
        <Fragment key={i}>{block(n, false, nodes[i - 1])}</Fragment>
      ))}
    </S.Flow>
  );

  const items = (nodes: DocNode[] = []) =>
    nodes.map((item, i) => <li key={i}>{stack(item.content)}</li>);

  const block = (n: DocNode, top: boolean, previous?: DocNode): ReactNode => {
    const a = n.attrs ?? {};
    switch (n.type) {
      case 'paragraph':
        return (
          <p>
            <Inline nodes={n.content} />
          </p>
        );
      case 'heading': {
        const level = Math.min(Math.max(Number(a.level ?? 1), 1), 4);
        // Only top-level headings are sections, as in the backend's chunking.
        const id = top ? headings[next++]?.anchor : undefined;
        return (
          <S.Heading as={`h${level + 1}` as 'h2'} id={id} $level={level}>
            <Inline nodes={n.content} />
          </S.Heading>
        );
      }
      case 'bulletList':
        return <ul>{items(n.content)}</ul>;
      case 'orderedList':
        return <ol start={a.start ? Number(a.start) : undefined}>{items(n.content)}</ol>;
      case 'taskList':
        return (
          <S.Tasks>
            {(n.content ?? []).map((item, i) => (
              <li key={i}>
                <input
                  type="checkbox"
                  checked={Boolean(item.attrs?.checked)}
                  readOnly
                  aria-label={t('folio.reader.task')}
                />
                {stack(item.content)}
              </li>
            ))}
          </S.Tasks>
        );
      case 'actionItem':
        return <ActionItem node={n} />;
      case 'blockquote':
        return <S.Quote>{stack(n.content)}</S.Quote>;
      case 'codeBlock':
        return (
          <S.Pre data-language={a.language ? String(a.language) : undefined}>
            <code>{(n.content ?? []).map((c) => c.text ?? '').join('')}</code>
          </S.Pre>
        );
      case 'horizontalRule':
        return <S.Rule />;
      case 'table':
        return (
          <S.TableWrap>
            <S.Table>
              <tbody>
                {(n.content ?? []).map((row, r) => (
                  <tr key={r}>
                    {(row.content ?? []).map((cell, c) => {
                      const Cell = cell.type === 'tableHeader' ? 'th' : 'td';
                      const ca = cell.attrs ?? {};
                      return (
                        <Cell
                          key={c}
                          colSpan={ca.colspan ? Number(ca.colspan) : undefined}
                          rowSpan={ca.rowspan ? Number(ca.rowspan) : undefined}
                          // The author picked this color: it is content, not a theme color.
                          style={ca.background ? { background: String(ca.background) } : undefined}
                        >
                          {stack(cell.content)}
                        </Cell>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </S.Table>
          </S.TableWrap>
        );
      default:
        return (
          <RichBlock node={n} previous={previous} headings={headings} childPages={childPages}>
            {stack}
          </RichBlock>
        );
    }
  };

  return (
    <S.Doc $size={size}>
      {(doc?.content ?? []).map((n, i, all) => (
        <Fragment key={i}>{block(n, true, all[i - 1])}</Fragment>
      ))}
    </S.Doc>
  );
}
