import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { ViewsChart } from '.';

describe('ViewsChart', () => {
  it('describes the range it draws', async () => {
    renderWithProviders(
      <ViewsChart
        days={[
          { day: '2026-10-20', views: 2, unique: 1 },
          { day: '2026-10-21', views: 5, unique: 3 },
        ]}
      />,
    );
    expect(
      await screen.findByRole('img', { name: 'Views over the last 2 days' }),
    ).toBeInTheDocument();
  });
});
