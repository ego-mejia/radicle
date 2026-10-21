import { fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { doc, p, t } from '../DocContent/testDoc';
import { FocusReader } from '.';

// About 4 minutes of reading.
const LONG = doc(p(t(Array(880).fill('palabra').join(' '))));

describe('FocusReader', () => {
  it('reads in one column with the minutes left, and exits', async () => {
    const onExit = vi.fn();
    renderWithProviders(
      <FocusReader
        title="Conecta un agente"
        kicker="how-to · Ingeniería"
        description="Paso a paso."
        content={LONG}
        childPages={[]}
        onExit={onExit}
      />,
    );
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Conecta un agente' }),
    ).toBeInTheDocument();
    expect(screen.getByText('how-to · Ingeniería')).toBeInTheDocument();
    expect(screen.getByText('4 min left')).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: 'Reading progress' })).toHaveAttribute(
      'aria-valuenow',
      '0',
    );

    Object.defineProperty(document.documentElement, 'scrollHeight', {
      value: 2000,
      configurable: true,
    });
    Object.defineProperty(window, 'innerHeight', { value: 1000, configurable: true });
    Object.defineProperty(window, 'scrollY', { value: 500, configurable: true });
    fireEvent.scroll(window);
    expect(screen.getByRole('progressbar', { name: 'Reading progress' })).toHaveAttribute(
      'aria-valuenow',
      '50',
    );
    expect(screen.getByText('2 min left')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Exit focus' }));
    expect(onExit).toHaveBeenCalled();
  });
});
