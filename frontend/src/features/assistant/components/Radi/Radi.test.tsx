import { fireEvent, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { Radi } from '.';

describe('Radi', () => {
  it('is a button that opens the help', async () => {
    const onClick = vi.fn();
    renderWithProviders(<Radi open={false} mood="idle" onClick={onClick} />);
    const radi = await screen.findByRole('button', { name: 'Ask Radi for help' });
    expect(radi).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(radi);
    expect(onClick).toHaveBeenCalled();
  });
});
