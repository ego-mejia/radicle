import {
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import {
  ChevronDown,
  ChevronRight,
  FileText,
  Folder,
  GripVertical,
  Radio,
  Shapes,
  Table2,
} from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  type FolioMoveIn,
  type FolioTreeItem,
  folioKeys,
  moveNode,
} from '../../../../services/api/folio';
import { type DropTarget, moveFor } from './moves';
import { NodeMenu } from '../NodeMenu';
import * as S from './style';

type Props = {
  space: string;
  items: FolioTreeItem[];
  /** The page being read, highlighted. */
  current?: string;
  /** Whether the reader may reorder (the space's `create` permission). */
  canMove?: boolean;
};

type RowProps = {
  space: string;
  item: FolioTreeItem;
  depth: number;
  current?: string;
  canMove: boolean;
  closed: Set<string>;
  toggle: (id: string) => void;
};

function Row({ space, item, depth, current, canMove, closed, toggle }: RowProps) {
  const { t } = useTranslation();
  const drag = useDraggable({ id: item.id, disabled: !canMove });
  const before = useDroppable({ id: `before:${item.id}`, disabled: !canMove });
  const into = useDroppable({ id: `into:${item.id}`, disabled: !canMove });
  const open = !closed.has(item.id);
  const hasChildren = item.children.length > 0;
  const Icon =
    item.kind === 'folder'
      ? Folder
      : item.kind === 'live_doc'
        ? Radio
        : item.kind === 'database'
          ? Table2
          : item.kind === 'whiteboard'
            ? Shapes
            : FileText;
  return (
    <li>
      <S.Row
        ref={into.setNodeRef}
        $depth={depth}
        $current={item.id === current}
        $over={into.isOver}
        $dragging={drag.isDragging}
      >
        <S.Before ref={before.setNodeRef} $over={before.isOver} aria-hidden />
        {hasChildren ? (
          <S.Toggle
            type="button"
            aria-expanded={open}
            aria-label={t(open ? 'folio.space.collapse' : 'folio.space.expand', {
              title: item.title,
            })}
            onClick={() => toggle(item.id)}
          >
            {open ? <ChevronDown aria-hidden /> : <ChevronRight aria-hidden />}
          </S.Toggle>
        ) : (
          <S.Spacer aria-hidden />
        )}
        {item.kind === 'folder' ? (
          <S.Label>
            <Icon aria-hidden />
            <S.Text>{item.title}</S.Text>
          </S.Label>
        ) : (
          <S.PageLink>
            <Link
              to="/folio/p/$page"
              params={{ page: `${item.id}-${item.slug}` }}
              aria-current={item.id === current ? 'page' : undefined}
            >
              {item.icon ? <span aria-hidden>{item.icon}</span> : <Icon aria-hidden />}
              <S.Text>{item.title}</S.Text>
            </Link>
          </S.PageLink>
        )}
        {canMove && (
          <S.Handle
            ref={drag.setNodeRef}
            type="button"
            aria-label={t('folio.space.move', { title: item.title })}
            {...drag.listeners}
            {...drag.attributes}
          >
            <GripVertical aria-hidden />
          </S.Handle>
        )}
        {canMove && <NodeMenu node={{ ...item, space }} />}
      </S.Row>
      {hasChildren && open && (
        <S.List>
          {item.children.map((child) => (
            <Row
              space={space}
              key={child.id}
              item={child}
              depth={depth + 1}
              current={current}
              canMove={canMove}
              closed={closed}
              toggle={toggle}
            />
          ))}
        </S.List>
      )}
    </li>
  );
}

function RootDrop() {
  const { t } = useTranslation();
  const drop = useDroppable({ id: 'root' });
  return (
    <S.Root ref={drop.setNodeRef} $over={drop.isOver}>
      {t('folio.space.dropRoot')}
    </S.Root>
  );
}

/** The space's pages and folders; with `canMove`, drag a row to reorder or nest it. */
export function SpaceTree({ space, items, current, canMove = false }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [closed, setClosed] = useState<Set<string>>(new Set());
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor),
  );
  const move = useMutation({
    mutationFn: ({ id, body }: { id: string; body: FolioMoveIn }) => moveNode(id, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: folioKeys.tree(space) }),
    onError: (e) => toast(errorMessage(e), 'error'),
  });

  const toggle = (id: string) =>
    setClosed((prev) => {
      const next = new Set(prev);
      if (!next.delete(id)) next.add(id);
      return next;
    });

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over) return;
    const body = moveFor(String(active.id), String(over.id) as DropTarget, items);
    if (body) move.mutate({ id: String(active.id), body });
  };

  if (!items.length) return <S.Empty>{t('folio.space.emptyTree')}</S.Empty>;
  return (
    <DndContext sensors={sensors} onDragEnd={onDragEnd}>
      <S.Nav aria-label={t('folio.space.tree')}>
        <S.List>
          {items.map((item) => (
            <Row
              space={space}
              key={item.id}
              item={item}
              depth={0}
              current={current}
              canMove={canMove}
              closed={closed}
              toggle={toggle}
            />
          ))}
        </S.List>
        {canMove && <RootDrop />}
      </S.Nav>
    </DndContext>
  );
}
