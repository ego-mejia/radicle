import { fireEvent, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { McpTool } from '../../../../services/api/admin';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { McpToolPicker } from '.';

const TOOLS: McpTool[] = [
  { name: 'whoami', group: 'context', read_only: true, description: 'Who you are' },
  { name: 'get_ticket', group: 'tickets', read_only: true, description: 'Read a ticket' },
  { name: 'create_ticket', group: 'tickets', read_only: false, description: 'Create one' },
];

vi.mock('../../../../services/api/admin', async (original) => ({
  ...(await original<typeof import('../../../../services/api/admin')>()),
  fetchMcpTools: () => Promise.resolve(TOOLS),
}));

let last: string[] | null = null;
function Harness({ initial }: { initial: string[] | null }) {
  const [value, setValue] = useState(initial);
  return (
    <McpToolPicker
      value={value}
      onChange={(next) => {
        last = next;
        setValue(next);
      }}
    />
  );
}

describe('McpToolPicker', () => {
  it('starts with every tool and narrows to read only', async () => {
    renderWithProviders(<Harness initial={null} />);
    const all = await screen.findByRole('checkbox', { name: /All tools/ });
    expect(all).toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'create_ticket' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Read only' }));
    expect(last).toEqual(['whoami', 'get_ticket']);
    expect(all).not.toBeChecked();
    expect(screen.getByRole('checkbox', { name: 'create_ticket' })).not.toBeChecked();
    expect(screen.getByText('2 of 3 tools allowed')).toBeInTheDocument();
  });

  it('turns a whole group on or off', async () => {
    renderWithProviders(<Harness initial={['whoami']} />);
    const group = await screen.findByRole('checkbox', { name: 'Tickets' });
    fireEvent.click(group);
    expect(last).toEqual(['whoami', 'get_ticket', 'create_ticket']);
    fireEvent.click(group);
    expect(last).toEqual(['whoami']);
    fireEvent.click(screen.getByRole('checkbox', { name: /All tools/ }));
    expect(last).toBeNull();
  });
});
