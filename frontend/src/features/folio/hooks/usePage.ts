import { useQuery } from '@tanstack/react-query';
import type { DocNode } from '../components/DocContent/anchors';
import {
  type FolioTreeItem,
  fetchDraft,
  fetchNode,
  fetchSpace,
  fetchTree,
  fetchVersions,
  folioKeys,
} from '../../../services/api/folio';

function findIn(items: FolioTreeItem[], id: string): FolioTreeItem | undefined {
  for (const item of items) {
    if (item.id === id) return item;
    const found = findIn(item.children, id);
    if (found) return found;
  }
  return undefined;
}

/** Everything the reading view needs: the node, its space, who published it, the pages
 * under it and, before the first publish, the draft (for those who can edit). */
export function usePage(id: string) {
  const node = useQuery({ queryKey: folioKeys.node(id), queryFn: () => fetchNode(id) });
  const key = node.data?.space ?? '';
  const published = node.data?.version != null;
  // A live doc is never published: everyone reads what is written now.
  const kind = node.data?.kind;
  const live = kind === 'live_doc' || kind === 'database' || kind === 'whiteboard';
  const space = useQuery({
    queryKey: folioKeys.space(key),
    queryFn: () => fetchSpace(key),
    enabled: !!key,
  });
  const versions = useQuery({
    queryKey: folioKeys.versions(id),
    queryFn: () => fetchVersions(id),
    enabled: published,
  });
  const draft = useQuery({
    queryKey: folioKeys.draft(id),
    queryFn: () => fetchDraft(id),
    enabled: node.isSuccess && !published && !live,
  });
  const tree = useQuery({
    queryKey: folioKeys.tree(key),
    queryFn: () => fetchTree(key),
    enabled: !!key,
  });

  const content = (published || live ? node.data?.content_json : draft.data?.content_json) as
    DocNode | null | undefined;
  return {
    node,
    space: space.data,
    canEdit: node.data?.can_edit ?? false,
    author: versions.data?.[0]?.author ?? null,
    draft,
    isDraft: !published && !live,
    content,
    metadata: published ? node.data?.metadata : draft.data?.metadata,
    children: tree.data ? (findIn(tree.data, id)?.children ?? []) : [],
  };
}
