import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { TICKET } from '../../../../test/fixtures';
import type { TicketSummary } from '../../../../services/api/types';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { FlashContext, useFlash } from '../../hooks/flash';
import { TicketCard } from '.';

function Card({ ticketKey }: { ticketKey: string }) {
  return (
    <TicketCard
      ticket={{ ...TICKET, key: ticketKey } as unknown as TicketSummary}
      flash={useFlash(ticketKey)}
    />
  );
}

describe('TicketCard flash', () => {
  it('flashes only the card that moved, brighter when it is done', async () => {
    renderWithProviders(
      <FlashContext.Provider value={{ key: 'PA-2', kind: 'done' }}>
        <Card ticketKey="PA-1" />
        <Card ticketKey="PA-2" />
      </FlashContext.Provider>,
    );
    expect(await screen.findByLabelText(/^PA-1 /)).not.toHaveAttribute('data-flash');
    expect(screen.getByLabelText(/^PA-2 /)).toHaveAttribute('data-flash', 'done');
  });
});
