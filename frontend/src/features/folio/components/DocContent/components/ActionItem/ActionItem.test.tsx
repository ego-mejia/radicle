import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../../../test/renderWithProviders';
import { ActionItem } from '.';

describe('ActionItem', () => {
  it('shows the text, the person and a late date', async () => {
    renderWithProviders(
      <ActionItem
        node={{
          type: 'actionItem',
          attrs: { id: 'ai-1', done: false, assignee: 'ana', due: '2020-01-02' },
          content: [{ type: 'text', text: 'Mandar el contrato' }],
        }}
      />,
    );
    expect(await screen.findByText('Mandar el contrato')).toBeInTheDocument();
    expect(screen.getByText('@ana')).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: 'Action item' })).not.toBeChecked();
    expect(screen.getByTitle('Due')).toHaveTextContent('2020');
  });

  it('checks done items', async () => {
    renderWithProviders(
      <ActionItem node={{ type: 'actionItem', attrs: { id: 'ai-2', done: true }, content: [] }} />,
    );
    expect(await screen.findByRole('checkbox', { name: 'Action item' })).toBeChecked();
  });
});
