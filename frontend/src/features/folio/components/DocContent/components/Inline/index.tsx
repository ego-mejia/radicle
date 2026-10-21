import type { ReactNode } from 'react';
import type { DocMark, DocNode } from '../../anchors';
import { Formula } from '../../../Formula';
import { TicketChip } from '../../../TicketChip';
import * as S from './style';
import { toneOf } from './tone';

function wrap(mark: DocMark, child: ReactNode, key: number): ReactNode {
  switch (mark.type) {
    case 'bold':
      return <strong key={key}>{child}</strong>;
    case 'italic':
      return <em key={key}>{child}</em>;
    case 'strike':
      return <s key={key}>{child}</s>;
    case 'underline':
      return <u key={key}>{child}</u>;
    case 'code':
      return <S.Code key={key}>{child}</S.Code>;
    case 'link': {
      const href = String(mark.attrs?.href ?? '#');
      const external = /^https?:\/\//.test(href);
      return (
        <a
          key={key}
          href={href}
          {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
        >
          {child}
        </a>
      );
    }
    default:
      return child;
  }
}

/** Text with its marks, mentions, statuses, ticket smart links and line breaks. */
export function Inline({ nodes }: { nodes?: DocNode[] }) {
  return (
    <>
      {(nodes ?? []).map((n, i) => {
        if (n.type === 'hardBreak') return <br key={i} />;
        if (n.type === 'mention')
          return <S.Mention key={i}>@{String(n.attrs?.handle ?? '')}</S.Mention>;
        if (n.type === 'status')
          return (
            <S.Status key={i} $tone={toneOf(String(n.attrs?.color ?? 'grey'))}>
              {String(n.attrs?.text ?? '')}
            </S.Status>
          );
        if (n.type === 'ticket')
          return <TicketChip key={i} ticketKey={String(n.attrs?.key ?? '')} />;
        if (n.type === 'inlineFormula')
          return <Formula key={i} latex={String(n.attrs?.latex ?? '')} inline />;
        if (n.type !== 'text') return null;
        return (n.marks ?? []).reduceRight<ReactNode>(
          (child, mark, m) => wrap(mark, child, m),
          <span key={i}>{n.text}</span>,
        );
      })}
    </>
  );
}
