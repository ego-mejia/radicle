import type {
  Board,
  BoardStatus,
  Category,
  ColumnConf,
  TicketType,
  TransitionOption,
} from '../services/api/types';

/** Whether a status (by name and ticket type) belongs to a column of the board. */
export function columnHolds(
  board: Board,
  column: ColumnConf,
  status: { name: string; category: Category },
  type: TicketType,
): boolean {
  if ((column.categories ?? []).includes(status.category)) return true;
  const match = board.statuses.find((s) => s.name === status.name && s.type === type);
  return Boolean(match && (column.status_ids ?? []).includes(match.id));
}

/** The column a status shows in: the first one that holds it, or -1. */
export function columnIndexOf(
  board: Board,
  status: { name: string; category: Category },
  type: TicketType,
): number {
  return board.columns.findIndex((column) => columnHolds(board, column, status, type));
}

/** Transitions of a ticket that land in `column`. */
export function optionsFor(
  board: Board,
  columnIndex: number,
  options: TransitionOption[],
  type: TicketType,
): TransitionOption[] {
  if (!board.columns[columnIndex]) return [];
  return options.filter(
    (o) => columnIndexOf(board, { name: o.to_status, category: o.category }, type) === columnIndex,
  );
}

/** The category that best describes a column, for its icon. */
export function columnCategory(board: Board, column: ColumnConf): Category {
  const categories = new Set<Category>(column.categories ?? []);
  for (const id of column.status_ids ?? []) {
    const status = board.statuses.find((s: BoardStatus) => s.id === id);
    if (status) categories.add(status.category);
  }
  if (categories.has('in_progress')) return 'in_progress';
  if (categories.size === 1 && categories.has('done')) return 'done';
  if (categories.has('todo')) return 'todo';
  return categories.has('done') ? 'done' : 'in_progress';
}
