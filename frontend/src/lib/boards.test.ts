import { describe, expect, it } from 'vitest';
import type { Board, TransitionOption } from '../services/api/types';
import { columnCategory, columnHolds, optionsFor } from './boards';

const board = {
  statuses: [
    { id: 's1', name: 'To Do', type: 'task', category: 'todo' },
    { id: 's2', name: 'In Review', type: 'task', category: 'in_progress' },
    { id: 's3', name: 'Doing', type: 'task', category: 'in_progress' },
  ],
  columns: [
    { name: 'Backlog', status_ids: [], categories: ['todo'], wip_limit: null },
    { name: 'Review', status_ids: ['s2'], categories: [], wip_limit: 2 },
    { name: 'Rest', status_ids: ['s3'], categories: ['done'], wip_limit: null },
  ],
} as unknown as Board;

const option = (name: string, to: string, category: string) =>
  ({ name, to_status: to, category, available: true }) as TransitionOption;

describe('boards', () => {
  it('matches statuses by category or by id', () => {
    expect(columnHolds(board, board.columns[0]!, { name: 'X', category: 'todo' }, 'task')).toBe(
      true,
    );
    expect(
      columnHolds(board, board.columns[1]!, { name: 'In Review', category: 'in_progress' }, 'task'),
    ).toBe(true);
    expect(
      columnHolds(board, board.columns[1]!, { name: 'Doing', category: 'in_progress' }, 'task'),
    ).toBe(false);
  });

  it('keeps only the transitions that land in the column', () => {
    const options = [
      option('Review', 'In Review', 'in_progress'),
      option('Start', 'Doing', 'in_progress'),
    ];
    expect(optionsFor(board, 1, options, 'task').map((o) => o.name)).toEqual(['Review']);
    expect(optionsFor(board, 9, options, 'task')).toEqual([]);
  });

  it('puts a status in the first column that holds it', () => {
    const first = {
      ...board,
      columns: [
        board.columns[1]!,
        { name: 'Doing', categories: ['in_progress'], status_ids: [], wip_limit: null },
      ],
    } as unknown as Board;
    const options = [
      option('Review', 'In Review', 'in_progress'),
      option('Start', 'Doing', 'in_progress'),
    ];
    expect(optionsFor(first, 1, options, 'task').map((o) => o.name)).toEqual(['Start']);
  });

  it('a status named in a later column wins over an earlier category column', () => {
    const later = {
      ...board,
      columns: [
        { name: 'In Progress', categories: ['in_progress'], status_ids: [], wip_limit: null },
        board.columns[1]!,
      ],
    } as unknown as Board;
    const options = [
      option('Review', 'In Review', 'in_progress'),
      option('Start', 'Doing', 'in_progress'),
    ];
    expect(optionsFor(later, 0, options, 'task').map((o) => o.name)).toEqual(['Start']);
    expect(optionsFor(later, 1, options, 'task').map((o) => o.name)).toEqual(['Review']);
  });

  it('picks an icon category for mixed columns', () => {
    expect(columnCategory(board, board.columns[0]!)).toBe('todo');
    expect(columnCategory(board, board.columns[2]!)).toBe('in_progress');
  });
});
