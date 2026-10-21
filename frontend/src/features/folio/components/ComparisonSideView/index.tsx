import { NodeViewContent, NodeViewWrapper, type NodeViewProps } from '@tiptap/react';
import { useTranslation } from 'react-i18next';
import * as S from './style';

/** One side of a comparison in the editor: its heading, then its blocks. */
export function ComparisonSideView({ node, updateAttributes, editor }: NodeViewProps) {
  const { t } = useTranslation();
  return (
    <NodeViewWrapper as="section" data-folio="comparisonSide">
      <S.Title
        value={String(node.attrs.title ?? '')}
        placeholder={t('folio.editor.panel.sideTitle')}
        aria-label={t('folio.editor.panel.sideTitle')}
        readOnly={!editor.isEditable}
        onChange={(e) => updateAttributes({ title: e.target.value || null })}
      />
      <NodeViewContent />
    </NodeViewWrapper>
  );
}
