import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';
import { Pencil } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { incomplete } from '../../editor/schema';
import { BlockPanel } from '../BlockPanel';
import { BlockFields } from '../BlockPanel/components/BlockFields';
import { type VisualAttrs, VisualFields } from '../BlockPanel/components/VisualFields';
import { ChartBlock } from '../ChartBlock';
import type { ChartKind } from '../ChartBlock/components/ChartView';
import { tableData } from '../ChartBlock/tableData';
import { DocContent } from '../DocContent';
import type { DocNode } from '../DocContent/anchors';
import { Formula } from '../Formula';
import * as S from './style';

/** A visual block inside the editor: what the reader will see, what it still needs
 * before it is saved, and its side panel. */
export function SuiteNodeView({ node, selected, editor, getPos, updateAttributes }: NodeViewProps) {
  const { t } = useTranslation();
  const type = node.type.name;
  const json = node.toJSON() as DocNode;
  const missing = incomplete(node.toJSON());
  // A new visual or page list opens its panel: it can't be saved without what it asks.
  const [open, setOpen] = useState(
    (type === 'visual' || type === 'pageList') && missing !== null && missing !== 'code',
  );
  const panel = open ? (
    <BlockPanel
      title={t(`folio.editor.blocks.${type}`)}
      wide={type === 'visual'}
      onClose={() => setOpen(false)}
    >
      {type === 'visual' ? (
        <VisualFields attrs={node.attrs as VisualAttrs} onChange={updateAttributes} />
      ) : (
        <BlockFields type={type} attrs={node.attrs} onChange={updateAttributes} />
      )}
    </BlockPanel>
  ) : null;

  if (type === 'inlineFormula') {
    return (
      <NodeViewWrapper
        as="span"
        data-folio="inlineFormula"
        onClick={() => editor.isEditable && setOpen(true)}
      >
        <Formula latex={String(node.attrs.latex)} inline />
        {panel}
      </NodeViewWrapper>
    );
  }
  // A chart drawn from a table reads the block right before it, as the reader does.
  const fromTable = type === 'chart' && node.attrs.source === 'table';
  const previous = () => {
    const pos = typeof getPos === 'function' ? getPos() : undefined;
    if (pos === undefined) return undefined;
    const $pos = editor.state.doc.resolve(pos);
    const index = $pos.index();
    return index > 0 ? ($pos.parent.child(index - 1).toJSON() as DocNode) : undefined;
  };
  return (
    <NodeViewWrapper data-folio={type} contentEditable={false}>
      <S.Block $selected={selected}>
        {editor.isEditable ? (
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
      {panel}
    </NodeViewWrapper>
  );
}
