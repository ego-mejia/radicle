import { useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { Spinner } from '../../../../components/ui/Spinner';
import {
  type FolioDoc,
  type FolioTreeItem,
  fetchTree,
  folioKeys,
  queryDocs,
} from '../../../../services/api/folio';
import { sectionQuery } from '../../sections';
import * as S from './style';

type Meta = { description?: string };
const href = (doc: FolioDoc) => `/folio/p/${doc.id}-${doc.slug}`;

function folders(items: FolioTreeItem[], out = new Map<string, string>()) {
  for (const item of items) {
    if (item.kind === 'folder') out.set(item.id, item.title);
    folders(item.children, out);
  }
  return out;
}

type Props = {
  space: string;
  /** Shown above the modules, e.g. Radi's suggestion about a page that went stale. */
  notice?: ReactNode;
};

/** The Docs section (RAD-57): the reference pages grouped by the folder they live in, one
 * card per module or app. */
export function DocsSection({ space, notice }: Props) {
  const { t } = useTranslation();
  const docs = useQuery({
    queryKey: ['folio', 'section', space, 'docs', 'all'],
    queryFn: async () => (await queryDocs(sectionQuery(space, 'docs', '', 'title ASC'), 100)).items,
  });
  const tree = useQuery({ queryKey: folioKeys.tree(space), queryFn: () => fetchTree(space) });

  if (docs.isPending || tree.isPending) return <Spinner />;
  if (docs.isError)
    return <EmptyState title={t('folio.sectionDocs.error')} text={docs.error.message} />;
  if (!docs.data.length)
    return (
      <EmptyState title={t('folio.sectionDocs.empty')} text={t('folio.sectionDocs.emptyHint')} />
    );

  const general = t('folio.docsSection.general');
  const names = tree.data ? folders(tree.data) : new Map<string, string>();
  const groups = new Map<string, FolioDoc[]>();
  for (const doc of docs.data) {
    const group = (doc.parent_id && names.get(doc.parent_id)) || general;
    groups.set(group, [...(groups.get(group) ?? []), doc]);
  }
  const ordered = [...groups.entries()].sort(
    ([a], [b]) => Number(a === general) - Number(b === general) || a.localeCompare(b),
  );

  return (
    <S.Wrap>
      {notice}
      <S.Grid>
        {ordered.map(([group, items]) => (
          <S.Module key={group} aria-labelledby={`docs-${group}`}>
            <S.ModuleHead>
              <S.Mark aria-hidden>{group.slice(0, 1).toUpperCase()}</S.Mark>
              <h2 id={`docs-${group}`}>{group}</h2>
              <small>{items.length}</small>
            </S.ModuleHead>
            {items.map((doc) => (
              <S.Row key={doc.id} to={href(doc)}>
                <b>{doc.title}</b>
                {(doc.metadata as Meta | null)?.description && (
                  <span>{(doc.metadata as Meta).description}</span>
                )}
              </S.Row>
            ))}
          </S.Module>
        ))}
      </S.Grid>
    </S.Wrap>
  );
}
