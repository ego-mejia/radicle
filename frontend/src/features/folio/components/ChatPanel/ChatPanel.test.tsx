import { fireEvent, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { ChatPanel } from '.';

vi.mock('../DocsChat', () => ({ DocsChat: () => <p>chat</p> }));

function Harness({ onClose }: { onClose: () => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button onClick={() => setOpen(true)}>open</button>
      <ChatPanel
        open={open}
        onClose={() => {
          onClose();
          setOpen(false);
        }}
      />
    </>
  );
}

describe('ChatPanel', () => {
  it('stays mounted while hidden and closes with Escape or its button', async () => {
    const onClose = vi.fn();
    renderWithProviders(<Harness onClose={onClose} />);
    expect(await screen.findByText('chat')).not.toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'open' }));
    expect(screen.getByText('chat')).toBeVisible();
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.getByText('chat')).not.toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'open' }));
    fireEvent.click(screen.getByRole('button', { name: 'Close the chat' }));
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});
