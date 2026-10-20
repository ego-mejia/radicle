import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { NewUserModal } from '.';

vi.mock('../../../../services/api/admin', async (original) => ({
  ...(await original<typeof import('../../../../services/api/admin')>()),
  fetchMcpTools: () =>
    Promise.resolve([
      { name: 'whoami', group: 'context', read_only: true, description: 'Who you are' },
      { name: 'create_ticket', group: 'tickets', read_only: false, description: 'Create one' },
    ]),
}));

describe('NewUserModal', () => {
  it('creates an agent with only the chosen MCP tools', async () => {
    const onCreate = vi.fn().mockResolvedValue(undefined);
    renderWithProviders(
      <NewUserModal kind="human" choose onClose={() => {}} onCreate={onCreate} />,
    );
    expect(await screen.findByLabelText('Email')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('radio', { name: /Agent \(LLM or worker\)/ }));
    expect(screen.queryByLabelText('Email')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Reader' } });
    fireEvent.change(screen.getByLabelText('Handle'), { target: { value: 'Reader-Bot' } });
    fireEvent.click(await screen.findByRole('button', { name: 'Read only' }));
    fireEvent.click(screen.getByRole('button', { name: 'Create' }));
    await waitFor(() =>
      expect(onCreate).toHaveBeenCalledWith(
        expect.objectContaining({ kind: 'agent', handle: 'reader-bot', mcp_tools: ['whoami'] }),
      ),
    );
  });
});
