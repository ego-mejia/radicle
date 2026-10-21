import { createRef } from 'react';
import { act, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { BLOCKS } from '../../editor/blocks';
import { SlashMenu, type SlashMenuHandle } from '.';

const items = BLOCKS.slice(0, 3);

describe('SlashMenu', () => {
  it('moves with the arrows and picks with Enter', async () => {
    const command = vi.fn();
    const ref = createRef<SlashMenuHandle>();
    renderWithProviders(<SlashMenu ref={ref} items={items} command={command} />);
    expect(await screen.findByRole('option', { name: 'Text' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    act(() => {
      ref.current?.onKeyDown(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
    });
    expect(screen.getByRole('option', { name: 'Heading 1' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    act(() => {
      ref.current?.onKeyDown(new KeyboardEvent('keydown', { key: 'ArrowUp' }));
      ref.current?.onKeyDown(new KeyboardEvent('keydown', { key: 'ArrowUp' }));
    });
    act(() => {
      ref.current?.onKeyDown(new KeyboardEvent('keydown', { key: 'Enter' }));
    });
    expect(command).toHaveBeenCalledWith(items[2]);
  });

  it('picks with a click and says when nothing matches', async () => {
    const command = vi.fn();
    const { unmount } = renderWithProviders(<SlashMenu items={items} command={command} />);
    await userEvent.click(await screen.findByRole('option', { name: 'Heading 2' }));
    expect(command).toHaveBeenCalledWith(items[2]);
    unmount();
    renderWithProviders(<SlashMenu items={[]} command={command} />);
    expect(await screen.findByText('No block matches')).toBeInTheDocument();
  });
});
