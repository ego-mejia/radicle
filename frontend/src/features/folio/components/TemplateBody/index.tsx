import { Placeholder } from '@tiptap/extensions';
import { EditorContent, useEditor } from '@tiptap/react';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { BLOCKS } from '../../editor/blocks';
import { folioExtensions } from '../../editor/extensions';
import { toFolioDoc } from '../../editor/schema';
import { SlashCommand } from '../../editor/slash';
import { EditorProse } from '../EditorProse';

type Props = {
  content: Record<string, unknown> | null;
  onChange: (doc: Record<string, unknown>) => void;
};

/** A page template's document in the same editor as pages, with the / menu. Templates
 * have no page to upload files to, so images and files are left out. */
export function TemplateBody({ content, onChange }: Props) {
  const { t } = useTranslation();
  const extensions = useMemo(
    () => [
      ...folioExtensions(),
      Placeholder.configure({ placeholder: t('folio.editor.bodyPlaceholder') }),
      SlashCommand.configure({ items: BLOCKS }),
    ],
    // Built once, like the page editor.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );
  const editor = useEditor({
    extensions,
    content: content ?? undefined,
    onUpdate: ({ editor: e }) => onChange(toFolioDoc(e.getJSON()) as Record<string, unknown>),
  });
  return (
    <EditorProse>
      <EditorContent editor={editor} aria-label={t('folio.templates.content')} />
    </EditorProse>
  );
}
