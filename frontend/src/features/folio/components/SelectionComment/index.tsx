import { MessageSquarePlus } from 'lucide-react';
import { type RefObject, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MarkdownEditor, type MentionOption } from '../../../../components/Markdown/MarkdownEditor';
import { Button } from '../../../../components/ui/Button';
import type { FolioAnchor } from '../../../../services/api/folioComments';
import { anchorFromSelection } from '../../hooks/textAnchor';
import * as S from './style';

type Props = {
  container: RefObject<HTMLElement | null>;
  mentions: MentionOption[];
  onComment: (anchor: FolioAnchor, body: string) => Promise<unknown>;
};

type Picked = { anchor: FolioAnchor; top: number; left: number };

/** Select text in the page and a "Comment" button appears next to it; it opens a small
 * box that posts an inline comment anchored to that text. */
export function SelectionComment({ container, mentions, onComment }: Props) {
  const { t } = useTranslation();
  const [picked, setPicked] = useState<Picked | null>(null);
  const [writing, setWriting] = useState(false);
  const [body, setBody] = useState('');

  useEffect(() => {
    const root = container.current;
    if (!root) return;
    const pick = () => {
      if (writing) return;
      const selection = window.getSelection();
      const anchor = anchorFromSelection(root, selection);
      if (!anchor || !selection) return setPicked(null);
      const rect = selection.getRangeAt(0).getBoundingClientRect();
      setPicked({ anchor, top: rect.bottom + 6, left: rect.left });
    };
    root.addEventListener('mouseup', pick);
    root.addEventListener('keyup', pick);
    return () => {
      root.removeEventListener('mouseup', pick);
      root.removeEventListener('keyup', pick);
    };
  }, [container, writing]);

  if (!picked) return null;
  const close = () => {
    setPicked(null);
    setWriting(false);
    setBody('');
  };
  const send = async () => {
    if (!body.trim()) return;
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
        <S.Trigger
          type="button"
          aria-label={t('folio.comments.commentOn')}
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => setWriting(true)}
        >
          <MessageSquarePlus aria-hidden />
          {t('folio.comments.comment')}
        </S.Trigger>
      )}
    </S.Float>
  );
}
