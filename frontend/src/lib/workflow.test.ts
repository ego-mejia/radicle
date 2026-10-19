import { describe, expect, it } from 'vitest';
import type { WorkflowConf } from '../services/api/types';
import { freshRef, removedStatuses, toMermaid, unreachable, workflowErrors } from './workflow';

const W: WorkflowConf = {
  statuses: [
    { ref: 'to_do', name: 'To Do', category: 'todo', is_initial: true },
    { ref: 'doing', name: 'Doing', category: 'in_progress', is_initial: false },
    { ref: 'done', name: 'Done', category: 'done', is_initial: false },
    { ref: 'limbo', name: 'Limbo', category: 'todo', is_initial: false },
  ],
  transitions: [
    { ref: 'start', name: 'Start', from: 'to_do', to: 'doing' },
    { ref: 'close', name: 'Close', from: null, to: 'done' },
  ],
};

describe('workflow helpers', () => {
  it('finds unreachable statuses and validation errors', () => {
    expect(unreachable(W)).toEqual(['Limbo']);
    expect(workflowErrors(W)).toEqual([]);
    const broken = { ...W, statuses: W.statuses.map((s) => ({ ...s, is_initial: false })) };
    expect(workflowErrors(broken).map((e) => e.key)).toEqual(['workflow.errors.initial']);
  });

  it('makes fresh refs and lists removed statuses', () => {
    expect(freshRef('Doing', ['doing', 'doing_2'])).toBe('doing_3');
    expect(freshRef('En revisión', [])).toBe('en_revision');
    const after = { ...W, statuses: W.statuses.slice(0, 3) };
    expect(removedStatuses(W, after).map((s) => s.ref)).toEqual(['limbo']);
  });

  it('renders a mermaid flowchart', () => {
    const source = toMermaid(W, 'Any');
    expect(source).toContain('s_to_do -->|"Start"| s_doing');
    expect(source).toContain('any{{"Any"}} -.->|"Close"| s_done');
  });
});
