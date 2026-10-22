import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { ParticipantsStack } from '.';

const people = [
  { handle: 'fernando', name: 'Fernando Mejía', kind: 'human', role: 'admin' as const },
  { handle: 'ana', name: 'Ana', kind: 'human', role: 'admin' as const },
  { handle: 'luis', name: 'Luis', kind: 'human', role: 'editor' as const },
  { handle: 'docs-bot', name: 'Agente de docs', kind: 'agent', role: 'editor' as const },
  { handle: 'vera', name: 'Vera', kind: 'human', role: 'reader' as const },
];

describe('ParticipantsStack', () => {
  it('sums up admins and the rest, and lists everyone by role', async () => {
    renderWithProviders(<ParticipantsStack participants={people} everyoneRole="reader" />);
    expect(await screen.findByText('+1')).toBeInTheDocument();
    const trigger = screen.getByRole('button', { name: /2 admins/ });
    await userEvent.click(trigger);
    expect(await screen.findByText('Agente de docs')).toBeInTheDocument();
    expect(screen.getByText('@vera')).toBeInTheDocument();
    expect(screen.getByText(/Everyone can read/)).toBeInTheDocument();
  });
});
