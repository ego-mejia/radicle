import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { DocContent } from '../DocContent';
import { b, doc } from '../DocContent/testDoc';

describe('Timeline', () => {
  it('lays milestones out in order with their date and status', async () => {
    const items = [
      { date: '2026-01', title: 'Beta', status: 'done', text: 'Equipo interno' },
      { title: 'GA', status: 'planned' },
    ];
    renderWithProviders(<DocContent doc={doc(b('timeline', { items }))} />);
    const line = await screen.findByRole('list', { name: 'Timeline' });
    const [first, second] = within(line).getAllByRole('listitem');
    expect(first).toHaveTextContent('2026-01BetaDoneEquipo interno');
    expect(second).toHaveTextContent('GAPlanned');
  });
});
