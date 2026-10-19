import { DndContext, type DragEndEvent, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Plus, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../../../components/ui/Button';
import { Input, Select } from '../../../../../../components/ui/Input';
import { freshRef } from '../../../../../../lib/workflow';
import { CATEGORIES, type StatusConf } from '../../../../../../services/api/types';
import * as S from './style';

type Props = {
  statuses: StatusConf[];
  onChange: (statuses: StatusConf[], removedRef?: string) => void;
  readOnly: boolean;
};

/** Statuses in order: drag to reorder, rename, change category, mark the initial one. */
export function StatusList({ statuses, onChange, readOnly }: Props) {
  const { t } = useTranslation();
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));
  const update = (ref: string, patch: Partial<StatusConf>) =>
    onChange(statuses.map((s) => (s.ref === ref ? { ...s, ...patch } : s)));
  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    const from = statuses.findIndex((s) => s.ref === active.id);
    const to = statuses.findIndex((s) => s.ref === over.id);
    onChange(arrayMove(statuses, from, to));
  };
  const add = () => {
    const name = t('workflow.newStatus');
    const ref = freshRef(
      name,
      statuses.map((s) => s.ref),
    );
    onChange([...statuses, { ref, name, category: 'in_progress', is_initial: false }]);
  };

  return (
    <S.List>
      <DndContext sensors={sensors} onDragEnd={onDragEnd}>
        <SortableContext items={statuses.map((s) => s.ref)} strategy={verticalListSortingStrategy}>
          {statuses.map((status) => (
            <Row
              key={status.ref}
              status={status}
              readOnly={readOnly}
              onChange={(patch) => update(status.ref, patch)}
              onInitial={() =>
                onChange(statuses.map((s) => ({ ...s, is_initial: s.ref === status.ref })))
              }
              onRemove={() =>
                onChange(
                  statuses.filter((s) => s.ref !== status.ref),
                  status.ref,
                )
              }
            />
          ))}
        </SortableContext>
      </DndContext>
      {!readOnly && (
        <Button size="sm" onClick={add}>
          <Plus />
          {t('workflow.addStatus')}
        </Button>
      )}
    </S.List>
  );
}

type RowProps = {
  status: StatusConf;
  readOnly: boolean;
  onChange: (patch: Partial<StatusConf>) => void;
  onInitial: () => void;
  onRemove: () => void;
};

function Row({ status, readOnly, onChange, onInitial, onRemove }: RowProps) {
  const { t } = useTranslation();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: status.ref,
    disabled: readOnly,
  });
  return (
    <S.Row
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      $dragging={isDragging}
    >
      {!readOnly && (
        <S.Handle
          {...attributes}
          {...listeners}
          aria-label={t('workflow.reorder', { name: status.name })}
        >
          <GripVertical />
        </S.Handle>
      )}
      <Input
        aria-label={t('workflow.statusName')}
        value={status.name}
        disabled={readOnly}
        onChange={(e) => onChange({ name: e.target.value })}
      />
      <Select
        aria-label={t('workflow.category')}
        value={status.category}
        disabled={readOnly}
        onChange={(e) => onChange({ category: e.target.value as StatusConf['category'] })}
      >
        {CATEGORIES.map((c) => (
          <option key={c} value={c}>
            {t(`ticket.categories.${c}`)}
          </option>
        ))}
      </Select>
      <S.Initial>
        <input
          type="radio"
          name="initial-status"
          checked={Boolean(status.is_initial)}
          disabled={readOnly}
          onChange={onInitial}
        />
        {t('workflow.initial')}
      </S.Initial>
      <S.Ref title={t('workflow.refHint')}>{status.ref}</S.Ref>
      {!readOnly && (
        <IconButton label={t('workflow.removeStatus', { name: status.name })} onClick={onRemove}>
          <Trash2 />
        </IconButton>
      )}
    </S.Row>
  );
}
