import { autocompletion, type CompletionContext } from '@codemirror/autocomplete';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import { markdown } from '@codemirror/lang-markdown';
import { EditorState } from '@codemirror/state';
import { EditorView, keymap, placeholder as placeholderExt } from '@codemirror/view';
import { useEffect, useRef } from 'react';
import { Frame } from './style';

export type MentionOption = { handle: string; name: string };

/** Lets a parent insert text where the cursor is and swap it later (upload placeholders). */
export type EditorApi = {
  insert: (text: string) => void;
  replace: (from: string, to: string) => void;
};

type Props = {
  value: string;
  onChange: (value: string) => void;
  mentions?: MentionOption[];
  placeholder?: string;
  autoFocus?: boolean;
  /** Cmd/Ctrl+Enter. */
  onSubmit?: () => void;
  ariaLabel: string;
  /** Files pasted or dropped into the editor. */
  onFiles?: (files: File[]) => void;
  apiRef?: React.MutableRefObject<EditorApi | null>;
};

/** CodeMirror 6 markdown editor with @handle completion. */
export function MarkdownEditor({
  value,
  onChange,
  mentions = [],
  placeholder,
  autoFocus,
  onSubmit,
  ariaLabel,
  onFiles,
  apiRef,
}: Props) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const latest = useRef({ onChange, onSubmit, mentions, onFiles });
  latest.current = { onChange, onSubmit, mentions, onFiles };

  useEffect(() => {
    const complete = (ctx: CompletionContext) => {
      const word = ctx.matchBefore(/@[\w-]*/);
      if (!word || (word.from === word.to && !ctx.explicit)) return null;
      return {
        from: word.from + 1,
        options: latest.current.mentions.map((m) => ({ label: m.handle, detail: m.name })),
        validFor: /^[\w-]*$/,
      };
    };
    const takeFiles = (list: FileList | undefined | null) => {
      const files = Array.from(list ?? []);
      if (!files.length || !latest.current.onFiles) return false;
      latest.current.onFiles(files);
      return true;
    };
    const state = EditorState.create({
      doc: value,
      extensions: [
        history(),
        markdown(),
        EditorView.lineWrapping,
        autocompletion({ override: [complete], activateOnTyping: true }),
        keymap.of([
          {
            key: 'Mod-Enter',
            run: () => {
              latest.current.onSubmit?.();
              return true;
            },
          },
          ...defaultKeymap,
          ...historyKeymap,
        ]),
        placeholder ? placeholderExt(placeholder) : [],
        EditorView.contentAttributes.of({ 'aria-label': ariaLabel, 'aria-multiline': 'true' }),
        EditorView.domEventHandlers({
          paste: (event) => takeFiles(event.clipboardData?.files),
          drop: (event, editor) => {
            const pos = editor.posAtCoords({ x: event.clientX, y: event.clientY });
            if (pos !== null) editor.dispatch({ selection: { anchor: pos } });
            return takeFiles(event.dataTransfer?.files);
          },
        }),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) latest.current.onChange(update.state.doc.toString());
        }),
      ],
    });
    view.current = new EditorView({ state, parent: host.current! });
    if (apiRef) {
      apiRef.current = {
        insert: (text) => {
          const editor = view.current;
          if (!editor) return;
          const { from, to } = editor.state.selection.main;
          editor.dispatch({
            changes: { from, to, insert: text },
            selection: { anchor: from + text.length },
          });
        },
        replace: (from, to) => {
          const editor = view.current;
          if (!editor) return;
          const at = editor.state.doc.toString().indexOf(from);
          if (at >= 0) editor.dispatch({ changes: { from: at, to: at + from.length, insert: to } });
        },
      };
    }
    if (autoFocus) view.current.focus();
    return () => view.current?.destroy();
    // The editor owns its document after mount; external resets go through the effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const editor = view.current;
    if (editor && editor.state.doc.toString() !== value) {
      editor.dispatch({ changes: { from: 0, to: editor.state.doc.length, insert: value } });
    }
  }, [value]);

  return <Frame ref={host} />;
}
