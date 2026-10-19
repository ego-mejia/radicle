import { Plus, Settings2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Select } from '../../../../components/ui/Input';
import { SWIMLANES, type Board, type Swimlane } from '../../../../services/api/types';
import * as S from './style';

type Props = {
  boards: Board[];
  board: Board;
  activeFilters: string[];
  swimlane: Swimlane;
  isAdmin: boolean;
  onBoard: (id: string) => void;
  onFilters: (ids: string[]) => void;
  onSwimlane: (lane: Swimlane) => void;
  onConfigure: () => void;
  onCreate: () => void;
};

/** Board picker, quick filter toggles and swimlane choice. */
export function BoardToolbar({
  boards,
  board,
  activeFilters,
  swimlane,
  isAdmin,
  onBoard,
  onFilters,
  onSwimlane,
  onConfigure,
  onCreate,
}: Props) {
  const { t } = useTranslation();
  const toggle = (id: string) =>
    onFilters(
      activeFilters.includes(id) ? activeFilters.filter((x) => x !== id) : [...activeFilters, id],
    );
  return (
    <S.Bar>
      <Select
        aria-label={t('board.board')}
        value={board.id}
        onChange={(e) => onBoard(e.target.value)}
      >
        {boards.map((b) => (
          <option key={b.id} value={b.id}>
            {b.name}
            {b.kind === 'scrum' ? ' · Scrum' : ''}
          </option>
        ))}
      </Select>
      <S.Filters role="group" aria-label={t('board.quickFilters')}>
        {board.quick_filters.map((q) => (
          <S.Chip
            key={q.id}
            type="button"
            aria-pressed={activeFilters.includes(q.id)}
            $active={activeFilters.includes(q.id)}
            title={q.rql}
            onClick={() => toggle(q.id)}
          >
            {q.name}
          </S.Chip>
        ))}
      </S.Filters>
      <S.Spacer />
      <Select
        aria-label={t('board.swimlanes')}
        value={swimlane}
        onChange={(e) => onSwimlane(e.target.value as Swimlane)}
      >
        {SWIMLANES.map((lane) => (
          <option key={lane} value={lane}>
            {t(`board.lanes.${lane}`)}
          </option>
        ))}
      </Select>
      {isAdmin && (
        <>
          <Button size="sm" onClick={onConfigure}>
            <Settings2 />
            {t('board.configure')}
          </Button>
          <Button size="sm" variant="ghost" onClick={onCreate}>
            <Plus />
            {t('board.new')}
          </Button>
        </>
      )}
    </S.Bar>
  );
}
