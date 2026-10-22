import { useQuery } from '@tanstack/react-query';
import { createLink } from '@tanstack/react-router';
import { useTranslation } from 'react-i18next';
import { fetchTree, folioKeys, type FolioTreeItem } from '../../../../services/api/folio';
import * as S from './style';

const PagerLink = createLink(S.Card);

/** The pages next to this one in its folder (or at the space's top level), in tree order. */
function neighbors(tree: FolioTreeItem[], id: string): FolioTreeItem[] | undefined {
  if (tree.some((n) => n.id === id)) return tree;
  for (const n of tree) {
    const found = neighbors(n.children ?? [], id);
    if (found) return found;
  }
  return undefined;
}

/** "Previous" and "Next" at the end of a page: its siblings in the same folder (ADR 0044). */
export function PagePager({ space, nodeId }: { space: string; nodeId: string }) {
  const { t } = useTranslation();
  const { data: tree } = useQuery({
    queryKey: folioKeys.tree(space),
    queryFn: () => fetchTree(space),
  });
  const pages = (neighbors(tree ?? [], nodeId) ?? []).filter((n) => n.kind !== 'folder');
  const at = pages.findIndex((n) => n.id === nodeId);
  if (at < 0) return null;
  const prev = pages[at - 1];
  const next = pages[at + 1];
  if (!prev && !next) return null;
  const link = (n: FolioTreeItem, label: string, end: boolean) => (
    <PagerLink to="/folio/p/$page" params={{ page: `${n.id}-${n.slug}` }} $end={end}>
      <S.Label>{label}</S.Label>
      <b>
        {n.icon && <span aria-hidden>{n.icon} </span>}
        {n.title}
      </b>
    </PagerLink>
  );
  return (
    <S.Pager aria-label={t('folio.reader.pager')}>
      {prev ? link(prev, t('folio.reader.prev'), false) : <span />}
      {next && link(next, t('folio.reader.next'), true)}
    </S.Pager>
  );
}
