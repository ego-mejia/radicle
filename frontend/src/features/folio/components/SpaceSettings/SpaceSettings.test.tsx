import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { FolioSpace } from '../../../../services/api/folio';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SpaceSettings } from '.';

const SPACE = {
  key: 'docs',
  name: 'Docs',
  description: '',
  kind: 'team',
  icon: null,
  cover_asset_id: null,
  created_at: '2026-10-20T10:00:00Z',
  permissions: ['view', 'admin'],
  verify_days: 90,
} as FolioSpace;

describe('SpaceSettings', () => {
  it('saves the verification days and shows the API error', async () => {
    const calls = mockFetch({
      'PATCH /api/v1/folio/spaces/docs': (_req, body) =>
        (body as { verify_days: number }).verify_days > 730
          ? {
              status: 422,
              body: { status: 422, detail: 'A verification lasts 1 to 730 days', errors: [] },
            }
          : { status: 200, body: { ...SPACE, verify_days: 30 } },
    });
    renderWithProviders(<SpaceSettings space={SPACE} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Space settings' }));
    const input = screen.getByLabelText('Days a verification lasts');
    await userEvent.clear(input);
    await userEvent.type(input, '999');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByText('A verification lasts 1 to 730 days')).toBeInTheDocument();
    await userEvent.clear(input);
    await userEvent.type(input, '30');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByText('Settings saved')).toBeInTheDocument();
    expect(calls.at(-1)?.body).toEqual({ verify_days: 30 });
  });
});
