import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { StatusBadge } from '.';

describe('StatusBadge', () => {
  it('shows the statuses that say something', async () => {
    renderWithProviders(<StatusBadge status="verified" />);
    expect(await screen.findByText('Verified')).toBeInTheDocument();
  });

  it('hides published and draft on cards, but not on the page', async () => {
    renderWithProviders(
      <>
        <StatusBadge status="published" />
        <StatusBadge status="draft" />
        <StatusBadge status="outdated" />
      </>,
    );
    expect(await screen.findByText('Outdated')).toBeInTheDocument();
    expect(screen.queryByText('Published')).toBeNull();
    expect(screen.queryByText('Draft')).toBeNull();
    renderWithProviders(<StatusBadge status="published" always />);
    expect(await screen.findByText('Published')).toBeInTheDocument();
  });
});
