import { MessageSquarePlus, SquareCheckBig } from 'lucide-react';
import { type RefObject, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MarkdownEditor, type MentionOption } from '../../../../components/Markdown/MarkdownEditor';
import { Button } from '../../../../components/ui/Button';
import type { FolioAnchor } from '../../../../services/api/folioComments';
import { anchorFromSelection, sectionOf } from '../../hooks/textAnchor';
import { CreateTicketDialog } from '../CreateTicketDialog';
import * as S from './style';

type Props = {
  container: RefObject<HTMLElement | null>;
  mentions: MentionOption[];
  /** Without it (no comment permission) only "Create ticket" shows. */
  onComment?: (anchor: FolioAnchor, body: string) => Promise<unknown>;
  /** The page, to create Docket tickets from the selection (Folio 4.2). */
  ticketNode?: { id: string; anchors?: () => string[] };
};

type Picked = { anchor: FolioAnchor; section: string | null; top: number; left: number };

/** Select text in the page and "Comment" and "Create ticket" appear next to it: one posts
 * an inline comment anchored to that text, the other makes a Docket ticket linked to its
 * section. */
export function SelectionComment({ container, mentions, onComment, ticketNode }: Props) {
  const { t } = useTranslation();
  const [picked, setPicked] = useState<Picked | null>(null);
  const [writing, setWriting] = useState(false);
  const [body, setBody] = useState('');
  const [ticket, setTicket] = useState<Picked | null>(null);

  useEffect(() => {
    const root = container.current;
    if (!root) return;
    const pick = () => {
      if (writing || ticket) return;
      const selection = window.getSelection();
      const anchor = anchorFromSelection(root, selection);
      if (!anchor || !selection) return setPicked(null);
      const rect = selection.getRangeAt(0).getBoundingClientRect();
      const section = sectionOf(root, selection, ticketNode?.anchors?.());
      setPicked({ anchor, section, top: rect.bottom + 6, left: rect.left });
    };
    root.addEventListener('mouseup', pick);
    root.addEventListener('keyup', pick);
    return () => {
      root.removeEventListener('mouseup', pick);
      root.removeEventListener('keyup', pick);
    };
  }, [container, writing, ticket, ticketNode]);

  if (ticket && ticketNode) {
    return (
      <CreateTicketDialog
        nodeId={ticketNode.id}
        text={ticket.anchor.quote}
        anchor={ticket.section}
        onClose={() => setTicket(null)}
      />
    );
  }
  if (!picked || (!onComment && !ticketNode)) return null;
  const close = () => {
    setPicked(null);
    setWriting(false);
    setBody('');
  };
  const send = async () => {
    if (!body.trim() || !onComment) return;
    await onComment(picked.anchor, body);
    close();
  };

  return (
    <S.Float style={{ top: picked.top, left: picked.left }}>
      {writing ? (
        <S.Box role="dialog" aria-label={t('folio.comments.commentOn')}>
          <S.Quote>“{picked.anchor.quote}”</S.Quote>
          <MarkdownEditor
            value={body}
            onChange={setBody}
            mentions={mentions}
            onSubmit={() => void send()}
            placeholder={t('folio.comments.placeholder')}
            ariaLabel={t('folio.comments.new')}
            autoFocus
          />
          <S.Row>
            <Button size="sm" onClick={close}>
              {t('folio.comments.cancel')}
            </Button>
            <Button size="sm" variant="primary" disabled={!body.trim()} onClick={() => void send()}>
              {t('folio.comments.post')}
            </Button>
          </S.Row>
        </S.Box>
      ) : (
        <S.Triggers>
          {onComment ? (
            <S.Trigger
              type="button"
              aria-label={t('folio.comments.commentOn')}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => setWriting(true)}
            >
              <MessageSquarePlus aria-hidden />
              {t('folio.comments.comment')}
            </S.Trigger>
          ) : null}
          {ticketNode ? (
            <S.Trigger
              type="button"
              $secondary
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => {
                setTicket(picked);
                setPicked(null);
              }}
            >
              <SquareCheckBig aria-hidden />
              {t('folio.tickets.create')}
            </S.Trigger>
          ) : null}
        </S.Triggers>
      )}
    </S.Float>
  );
}
