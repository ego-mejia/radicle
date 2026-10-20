import { fireEvent, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { TokenReveal } from '.';

describe('TokenReveal', () => {
  it('shows the token once in a dialog and closes', async () => {
    const onClose = vi.fn();
    renderWithProviders(
      <TokenReveal token="rdc_abc" mcpUrl="http://localhost:8000/mcp" onClose={onClose} />,
    );
    const dialog = await screen.findByRole('dialog', { name: 'Your new token' });
    expect(dialog).toHaveTextContent('rdc_abc');
    expect(dialog).toHaveTextContent('claude mcp add');
    fireEvent.click(screen.getByRole('button', { name: 'Done, I copied it' }));
    expect(onClose).toHaveBeenCalled();
  });
});
