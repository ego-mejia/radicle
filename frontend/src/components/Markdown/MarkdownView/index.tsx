import { Children, isValidElement } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown, { type Components } from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';
import remarkGfm from 'remark-gfm';
import { checklistLines } from '../../../lib/checklist';
import type { ChecklistItem } from '../../../services/api/types';
import { Avatar } from '../../ui/Avatar';
import * as S from './style';

type Props = {
  children: string;
  /** Checklist as parsed by the API, in the same order as the task list items. */
  checklist?: ChecklistItem[];
  onToggle?: (index: number, checked: boolean) => void;
  readOnly?: boolean;
};

const MENTION = /(^|[^\w.@/])@([a-z0-9][a-z0-9_-]{1,31})/gi;

/** Highlights @mentions inside plain text children. */
function withMentions(children: React.ReactNode): React.ReactNode {
  return Children.map(children, (child) => {
    if (typeof child !== 'string') return child;
    const parts: React.ReactNode[] = [];
    let last = 0;
    for (const match of child.matchAll(MENTION)) {
      const start = (match.index ?? 0) + match[1]!.length;
      parts.push(child.slice(last, start));
      parts.push(
        <span className="mention" key={start}>
          @{match[2]}
        </span>,
      );
      last = start + match[2]!.length + 1;
    }
    parts.push(child.slice(last));
    return parts;
  });
}

function stripCheckbox(children: React.ReactNode): React.ReactNode {
  return Children.toArray(children).filter(
    (child) => !(isValidElement(child) && child.type === 'input'),
  );
}

export function MarkdownView({ children, checklist = [], onToggle, readOnly = false }: Props) {
  const { t } = useTranslation();
  // Index items by source line, not render order: React may render a component twice.
  const lines = checklistLines(children);

  const components: Components = {
    p: ({ children: c }) => <p>{withMentions(c)}</p>,
    li: ({ className, children: c, node }) => {
      if (!className?.includes('task-list-item')) return <li>{withMentions(c)}</li>;
      const line = (node?.position?.start.line ?? 0) - 1;
      const index = lines.get(line) ?? -1;
      const item = index >= 0 ? checklist[index] : undefined;
      const checked = item?.checked ?? false;
      return (
        <S.TaskItem className="task-list-item">
          <input
            type="checkbox"
            checked={checked}
            disabled={readOnly || !onToggle || !item}
            onChange={(e) => onToggle?.(index, e.target.checked)}
            aria-label={item?.text ?? ''}
          />
          <S.TaskText $checked={checked}>{withMentions(stripCheckbox(c))}</S.TaskText>
          {item?.assignee &&
            (item.assignee_unknown ? (
              <S.Unknown>{t('ticket.unknownHandle', { handle: item.assignee })}</S.Unknown>
            ) : (
              <Avatar handle={item.assignee} size={20} />
            ))}
        </S.TaskItem>
      );
    },
    a: ({ href, children: c }) => (
      <a href={href} target="_blank" rel="noreferrer noopener">
        {c}
      </a>
    ),
  };

  return (
    <S.Prose>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={components}
      >
        {children}
      </ReactMarkdown>
    </S.Prose>
  );
}
