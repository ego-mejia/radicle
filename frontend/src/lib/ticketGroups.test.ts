import { describe, expect, it } from 'vitest';
import type { TicketSummary } from '../services/api/types';
import { groupTickets, topLevel } from './ticketGroups';

const t = (key: string, extra: Partial<TicketSummary> = {}) =>
  ({ key, type: 'task', area: 'Backend', parent: null, ...extra }) as unknown as TicketSummary;

describe('ticket groups', () => {
  it('groups by a field with empty values last', () => {
    const groups = groupTickets(
      [t('PA-1', { area: null }), t('PA-2'), t('PA-3', { area: 'Mobile' }), t('PA-4')],
      'area',
    );
    expect(groups.map((g) => [g.label, g.tickets.map((x) => x.key)])).toEqual([
      ['Backend', ['PA-2', 'PA-4']],
      ['Mobile', ['PA-3']],
      [null, ['PA-1']],
    ]);
    expect(groupTickets([t('PA-1')], 'none')).toHaveLength(1);
  });

  it('nests subtickets whose parent is listed', () => {
    const rows = [t('PA-1'), t('PA-2', { parent: 'PA-1' }), t('PA-3', { parent: 'PA-9' })];
    expect(topLevel(rows).map((x) => x.key)).toEqual(['PA-1', 'PA-3']);
  });
});
