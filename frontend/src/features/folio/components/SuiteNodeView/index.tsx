import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';
import { Pencil } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { incomplete } from '../../editor/schema';
import { BlockPanel } from '../BlockPanel';
import { type VisualAttrs, VisualFields } from '../BlockPanel/components/VisualFields';
import { ChartBlock } from '../ChartBlock';
import type { ChartKind } from '../ChartBlock/components/ChartView';
import { tableData } from '../ChartBlock/tableData';
import { DocContent } from '../DocContent';
import type { DocNode } from '../DocContent/anchors';
import { Formula } from '../Formula';
import * as S from './style';

/** A visual block inside the editor: what the reader will see, and what it still needs
 * before it is saved. */
export function SuiteNodeView({ node, selected, editor, getPos, updateAttributes }: NodeViewProps) {
  const { t } = useTranslation();
  const type = node.type.name;
  // A new visual opens its panel: it needs a description before it is saved.
  const [open, setOpen] = useState(type === 'visual' && !node.attrs.description);
  const json = node.toJSON() as DocNode;
  if (node.type.name === 'inlineFormula') {
    return (
      <NodeViewWrapper as="span" data-folio="inlineFormula">
        <Formula latex={String(node.attrs.latex)} inline />
      </NodeViewWrapper>
    );
  }
  const missing = incomplete(node.toJSON());
  // A chart drawn from a table reads the block right before it, as the reader does.
  const fromTable = node.type.name === 'chart' && node.attrs.source === 'table';
  const previous = () => {
    const pos = typeof getPos === 'function' ? getPos() : undefined;
    if (pos === undefined) return undefined;
    const $pos = editor.state.doc.resolve(pos);
    const index = $pos.index();
    return index > 0 ? ($pos.parent.child(index - 1).toJSON() as DocNode) : undefined;
  };
  return (
    <NodeViewWrapper data-folio={node.type.name} contentEditable={false}>
      <S.Block $selected={selected}>
        {type === 'visual' && editor.isEditable ? (
          <S.Edit type="button" onClick={() => setOpen(true)}>
            <Pencil size={14} aria-hidden />
            {t('folio.editor.panel.edit')}
          </S.Edit>
        ) : null}
        {missing ? (
          <S.Missing>{t(`folio.editor.needs.${missing}`)}</S.Missing>
        ) : fromTable ? (
          <ChartBlock
            kind={String(node.attrs.kind) as ChartKind}
            title={node.attrs.title as string | null}
            data={tableData(previous())}
          />
        ) : (
          <DocContent doc={{ type: 'doc', content: [json] }} />
        )}
      </S.Block>
      {open && type === 'visual' ? (
        <BlockPanel title={t('folio.editor.blocks.visual')} wide onClose={() => setOpen(false)}>
          <VisualFields attrs={node.attrs as VisualAttrs} onChange={updateAttributes} />
        </BlockPanel>
      ) : null}
    </NodeViewWrapper>
  );
}
