import { NodeViewWrapper, type NodeViewProps } from '@tiptap/react';
import { EmbedCard } from '../EmbedCard';

/** The embed block inside the editor: the reader's card, and it keeps the title and
 * provider the preview found so the page's text and search have them. */
export function EmbedNodeView({ node, updateAttributes }: NodeViewProps) {
  const url = String(node.attrs.url);
  return (
    <NodeViewWrapper data-folio="embed" contentEditable={false}>
      <EmbedCard
        url={url}
        title={node.attrs.title as string | null}
        onPreview={(p) => {
          if (p.title !== node.attrs.title || (p.provider ?? null) !== node.attrs.provider) {
            updateAttributes({ title: p.title || null, provider: p.provider ?? null });
          }
        }}
      />
    </NodeViewWrapper>
  );
}
