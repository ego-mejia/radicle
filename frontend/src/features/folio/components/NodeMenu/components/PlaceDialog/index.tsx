import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../components/ui/Button';
import { Field } from '../../../../../../components/ui/Field';
import { Select } from '../../../../../../components/ui/Input';
import { Modal } from '../../../../../../components/ui/Modal';
import {
  fetchSpaces,
  fetchTree,
  folioKeys,
  type FolioTreeItem,
} from '../../../../../../services/api/folio';
import * as S from './style';

export type Place = { space: string; parent: string | null; includeChildren: boolean };

type Props = {
  mode: 'move' | 'copy';
  node: { id: string; title: string; kind: string; space: string };
  open: boolean;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (place: Place) => void;
};

/** Pages and folders of a tree, indented, leaving out `skip` and everything under it. */
function flatten(items: FolioTreeItem[], skip: string, depth = 0): [FolioTreeItem, number][] {
  return items
    .filter((i) => i.id !== skip && i.kind !== 'blog_post')
    .flatMap((i) => [
      [i, depth] as [FolioTreeItem, number],
      ...flatten(i.children, skip, depth + 1),
    ]);
}

/** Where to move or copy a node: a space you can write in and, for pages, a parent. */
export function PlaceDialog({ mode, node, open, busy, error, onClose, onSubmit }: Props) {
  const { t } = useTranslation();
  const [space, setSpace] = useState(node.space);
  const [parent, setParent] = useState('');
  const [includeChildren, setIncludeChildren] = useState(false);
  const spaces = useQuery({ queryKey: folioKeys.spaces, queryFn: fetchSpaces, enabled: open });
  const tree = useQuery({
    queryKey: folioKeys.tree(space),
    queryFn: () => fetchTree(space),
    enabled: open && node.kind !== 'blog_post',
  });
  const writable = (spaces.data ?? []).filter((s) => s.permissions.includes('create'));

  return (
    <Modal
      open={open}
      onOpenChange={(o) => !o && onClose()}
      title={t(`folio.organize.${mode}Title`, { title: node.title })}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            disabled={busy}
            onClick={() => onSubmit({ space, parent: parent || null, includeChildren })}
          >
            {t(`folio.organize.${mode}`)}
          </Button>
        </>
      }
    >
      <S.Form>
        <Field label={t('folio.organize.space')}>
          <Select
            value={space}
            onChange={(e) => {
              setSpace(e.target.value);
              setParent('');
            }}
          >
            {writable.map((s) => (
              <option key={s.key} value={s.key}>
                {s.name}
              </option>
            ))}
          </Select>
        </Field>
        {node.kind !== 'blog_post' && (
          <Field label={t('folio.organize.parent')}>
            <Select value={parent} onChange={(e) => setParent(e.target.value)}>
              <option value="">{t('folio.organize.topLevel')}</option>
              {flatten(tree.data ?? [], node.id).map(([item, depth]) => (
                <option key={item.id} value={item.id}>
                  {`${'— '.repeat(depth)}${item.title}`}
                </option>
              ))}
            </Select>
          </Field>
        )}
        {mode === 'copy' && node.kind !== 'blog_post' && (
          <S.Check>
            <input
              type="checkbox"
              checked={includeChildren}
              onChange={(e) => setIncludeChildren(e.target.checked)}
            />
            {t('folio.organize.includeChildren')}
          </S.Check>
        )}
        {error && <S.Error role="alert">{error}</S.Error>}
      </S.Form>
    </Modal>
  );
}
