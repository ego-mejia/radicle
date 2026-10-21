import { fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRef } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { rangeOf } from '../../hooks/textAnchor';
import { SelectionComment } from '.';

function Page({ onComment }: { onComment: () => Promise<unknown> }) {
  const ref = useRef<HTMLDivElement>(null);
  return (
    <>
      <div ref={ref} data-testid="page">
        <p>Crea el agente y conéctalo por MCP.</p>
      </div>
      <SelectionComment container={ref} mentions={[]} onComment={onComment} />
    </>
  );
}

describe('SelectionComment', () => {
  it('offers to comment on selected text and opens a box with the quote', async () => {
    const onComment = vi.fn(async () => undefined);
    renderWithProviders(<Page onComment={onComment} />);
    const page = await screen.findByTestId('page');
    expect(screen.queryByRole('button', { name: 'Comment on the selected text' })).toBeNull();

    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(rangeOf(page, 'conéctalo por MCP')!);
    fireEvent.mouseUp(page);

    await userEvent.click(
      await screen.findByRole('button', { name: 'Comment on the selected text' }),
    );
    const box = screen.getByRole('dialog', { name: 'Comment on the selected text' });
    expect(box).toHaveTextContent('“conéctalo por MCP”');
    expect(screen.getByRole('button', { name: 'Comment' })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(onComment).not.toHaveBeenCalled();
  });
});
