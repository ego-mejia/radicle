import { useMutation } from '@tanstack/react-query';
import type { Editor } from '@tiptap/react';
import { Sparkles } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Input } from '../../../../components/ui/Input';
import { Menu } from '../../../../components/ui/Menu';
import { Spinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { rewriteText, type RewriteMode } from '../../../../services/api/folioAi';
import { fromText } from '../../editor/fromText';
import { useEditorAi } from '../../hooks/useEditorAi';
import * as S from './style';

type Props = { editor: Editor; nodeId: string; space: string };
type Picked = { from: number; to: number; text: string; top: number; left: number };
const MODES: Exclude<RewriteMode, 'translate'>[] = ['clearer', 'shorter', 'formal'];

/** Select text while writing and an AI button offers to rewrite it (Folio 4.6). The
 * proposal replaces the selection only when you accept it. */
export function SelectionAi({ editor, nodeId, space }: Props) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const available = useEditorAi(space);
  const [picked, setPicked] = useState<Picked | null>(null);
  const [translating, setTranslating] = useState(false);
  const [language, setLanguage] = useState('');
  const rewrite = useMutation({
    mutationFn: ({ mode, lang }: { mode: RewriteMode; lang?: string }) =>
      rewriteText(nodeId, picked?.text ?? '', mode, lang),
  });
  const busy = rewrite.isPending || !!rewrite.data || rewrite.isError || translating;

  useEffect(() => {
    if (busy) return;
    const pick = () => {
      const { from, to, empty } = editor.state.selection;
      const text = editor.state.doc.textBetween(from, to, '\n\n').trim();
      if (empty || !text) return setPicked(null);
      const start = editor.view.coordsAtPos(from);
      setPicked({ from, to, text, top: start.top - 44, left: start.left });
    };
    // Not on blur: opening the menu takes the focus, and the selection is still there.
    editor.on('selectionUpdate', pick);
    return () => {
      editor.off('selectionUpdate', pick);
    };
  }, [editor, busy]);

  if (!available || !picked) return null;
  const close = () => {
    rewrite.reset();
    setTranslating(false);
    setPicked(null);
  };
  const accept = (text: string) => {
    const nodes = fromText(text);
    // One paragraph goes in as text, so a selection inside a line stays in that line.
    const [only] = nodes;
    const content = nodes.length === 1 && only?.type === 'paragraph' ? (only.content ?? []) : nodes;
    editor.chain().focus().insertContentAt({ from: picked.from, to: picked.to }, content).run();
    close();
  };

  return (
    <S.Float style={{ top: picked.top, left: picked.left }}>
      {!busy && (
        <Menu
          trigger={
            <S.Trigger type="button" onMouseDown={(e) => e.preventDefault()}>
              <Sparkles aria-hidden />
              {t('folio.ai.rewrite')}
            </S.Trigger>
          }
          items={[
            ...MODES.map((mode) => ({
              key: mode,
              label: t(`folio.ai.modes.${mode}`),
              onSelect: () => rewrite.mutate({ mode }),
            })),
            {
              key: 'translate',
              label: t('folio.ai.modes.translate'),
              onSelect: () => setTranslating(true),
            },
          ]}
        />
      )}
      {translating && !rewrite.isPending && !rewrite.data && !rewrite.isError && (
        <S.Box
          as="form"
          aria-label={t('folio.ai.modes.translate')}
          onSubmit={(e: React.FormEvent) => {
            e.preventDefault();
            if (language.trim()) rewrite.mutate({ mode: 'translate', lang: language.trim() });
          }}
        >
          <Input
            autoFocus
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            placeholder={t('folio.ai.languagePlaceholder')}
            aria-label={t('folio.ai.language')}
          />
          <S.Row>
            <Button size="sm" type="button" onClick={close}>
              {t('common.cancel')}
            </Button>
            <Button size="sm" variant="primary" type="submit" disabled={!language.trim()}>
              {t('folio.ai.modes.translate')}
            </Button>
          </S.Row>
        </S.Box>
      )}
      {(rewrite.isPending || rewrite.data || rewrite.isError) && (
        <S.Box role="dialog" aria-label={t('folio.ai.proposal')}>
          {rewrite.isPending && (
            <S.Muted role="status">
              <Spinner size={14} />
              {t('folio.ai.thinking')}
            </S.Muted>
          )}
          {rewrite.isError && <S.Error role="alert">{errorMessage(rewrite.error)}</S.Error>}
          {rewrite.data && <S.Proposal>{rewrite.data}</S.Proposal>}
          <S.Row>
            <Button size="sm" onClick={close}>
              {t('folio.ai.discard')}
            </Button>
            <Button
              size="sm"
              variant="primary"
              disabled={!rewrite.data}
              onClick={() => rewrite.data && accept(rewrite.data)}
            >
              {t('folio.ai.accept')}
            </Button>
          </S.Row>
        </S.Box>
      )}
    </S.Float>
  );
}
