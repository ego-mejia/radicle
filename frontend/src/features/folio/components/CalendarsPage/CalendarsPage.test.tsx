import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { AGENDA, CAL_ID, CALENDAR } from '../../calendar/fixtures';
import { CalendarsPage } from '.';

const SPACE = {
  key: 'eng',
  name: 'Ingeniería',
  description: '',
  kind: 'team',
  icon: null,
  cover_asset_id: null,
  created_at: '2026-10-20T10:00:00Z',
  permissions: ['view', 'create', 'admin'],
};
const ONCALL = { ...CALENDAR, id: 'c2', name: 'Guardias', color: 'orange', can_manage: false };

function api(space: object = SPACE, calendars: object[] = [CALENDAR, ONCALL]) {
  return mockFetch({
    'GET /api/v1/folio/spaces/eng': { status: 200, body: space },
    'GET /api/v1/folio/calendars': { status: 200, body: { items: calendars } },
    [`GET /api/v1/folio/calendars/${CAL_ID}/events`]: { status: 200, body: AGENDA },
    'GET /api/v1/folio/calendars/c2/events': { status: 200, body: { events: [], milestones: [] } },
  });
}

describe('CalendarsPage', () => {
  it('shows the first calendar and switches between them', async () => {
    api();
    renderWithProviders(<CalendarsPage spaceKey="eng" />);
    expect(await screen.findByRole('region', { name: 'Releases' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Calendar settings' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: 'Guardias' }));
    expect(await screen.findByRole('region', { name: 'Guardias' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Calendar settings' })).not.toBeInTheDocument();
  });

  it('opens the forms to add events and calendars', async () => {
    api();
    renderWithProviders(<CalendarsPage spaceKey="eng" />);
    await userEvent.click(await screen.findByRole('button', { name: 'New event' }));
    expect(await screen.findByRole('dialog', { name: 'New event' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    await userEvent.click(screen.getByRole('button', { name: 'New calendar' }));
    expect(await screen.findByRole('dialog', { name: 'New calendar' })).toBeInTheDocument();
  });

  it('tells readers there are no calendars yet', async () => {
    api({ ...SPACE, permissions: ['view'] }, []);
    renderWithProviders(<CalendarsPage spaceKey="eng" />);
    expect(await screen.findByText('No calendars yet')).toBeInTheDocument();
    expect(screen.getByText('A space admin can create calendars here.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'New calendar' })).not.toBeInTheDocument();
  });
});
