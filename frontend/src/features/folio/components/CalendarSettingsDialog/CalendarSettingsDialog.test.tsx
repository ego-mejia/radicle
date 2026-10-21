import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { CAL_ID, CALENDAR } from '../../calendar/fixtures';
import { CalendarSettingsDialog } from '.';

const URL = `/api/v1/folio/calendars/${CAL_ID}`;

describe('CalendarSettingsDialog', () => {
  it('creates a calendar with its Docket projects', async () => {
    const calls = mockFetch({ 'POST /api/v1/folio/calendars': { status: 201, body: CALENDAR } });
    const onSaved = vi.fn();
    renderWithProviders(
      <CalendarSettingsDialog space="eng" open onOpenChange={vi.fn()} onSaved={onSaved} />,
    );
    await userEvent.type(await screen.findByLabelText('Name'), 'Releases');
    await userEvent.selectOptions(screen.getByLabelText('Color'), 'Green');
    await userEvent.type(screen.getByLabelText('Docket projects'), 'pa, PB');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(CALENDAR));
    expect(calls[0]?.body).toEqual({
      space: 'eng',
      name: 'Releases',
      color: 'green',
      docket_projects: ['pa', 'PB'],
    });
  });

  it('shows the feed link, replaces it, and says why a save failed', async () => {
    const calls = mockFetch({
      [`POST ${URL}/ical-token`]: {
        status: 200,
        body: { ...CALENDAR, ical_path: '/ical/new.ics' },
      },
      [`PATCH ${URL}`]: {
        status: 422,
        body: { status: 422, detail: 'No Docket project ZZ you can see.', errors: [] },
      },
    });
    renderWithProviders(
      <CalendarSettingsDialog space="eng" calendar={CALENDAR} open onOpenChange={vi.fn()} />,
    );
    const feed = await screen.findByRole('textbox', { name: 'Feed link' });
    expect(feed).toHaveValue(`${window.location.origin}/ical/tok.ics`);
    await userEvent.click(screen.getByRole('button', { name: 'New link' }));
    expect(await screen.findByDisplayValue(/\/ical\/new\.ics$/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('ZZ');
    expect(calls.map((c) => c.method)).toEqual(['POST', 'PATCH']);
  });

  it('deletes after confirming', async () => {
    const calls = mockFetch({ [`DELETE ${URL}`]: { status: 200, body: null } });
    const onSaved = vi.fn();
    renderWithProviders(
      <CalendarSettingsDialog
        space="eng"
        calendar={CALENDAR}
        open
        onOpenChange={vi.fn()}
        onSaved={onSaved}
      />,
    );
    await userEvent.click(await screen.findByRole('button', { name: 'Delete' }));
    const confirm = screen.getByRole('dialog', { name: 'Delete this calendar?' });
    await userEvent.click(
      [...confirm.querySelectorAll('button')].find((b) => b.textContent === 'Delete')!,
    );
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(null));
    expect(calls[0]?.method).toBe('DELETE');
  });
});
