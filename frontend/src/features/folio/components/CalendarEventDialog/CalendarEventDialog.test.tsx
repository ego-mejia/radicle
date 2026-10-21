import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { AGENDA, CAL_ID } from '../../calendar/fixtures';
import { CalendarEventDialog } from '.';

const EVENTS = `/api/v1/folio/calendars/${CAL_ID}/events`;

describe('CalendarEventDialog', () => {
  it('adds an all-day event with an exclusive end', async () => {
    const calls = mockFetch({ [`POST ${EVENTS}`]: { status: 201, body: AGENDA.events[1] } });
    const onOpenChange = vi.fn();
    renderWithProviders(
      <CalendarEventDialog
        calendarId={CAL_ID}
        day={new Date(2026, 11, 14)}
        open
        onOpenChange={onOpenChange}
      />,
    );
    await userEvent.type(await screen.findByLabelText('Title'), 'Vacaciones');
    await userEvent.click(screen.getByLabelText('All day'));
    await userEvent.selectOptions(screen.getByLabelText('Category'), 'Vacation');
    await userEvent.type(screen.getByLabelText('People'), '@ana');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    expect(calls[0]?.body).toMatchObject({
      title: 'Vacaciones',
      all_day: true,
      category: 'vacation',
      start_at: '2026-12-14T00:00:00Z',
      end_at: '2026-12-15T00:00:00Z',
      people: ['ana'],
    });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('changes and deletes an event you may edit, and shows API errors', async () => {
    const event = AGENDA.events[0]!;
    const calls = mockFetch({
      [`PATCH ${EVENTS}/${event.id}`]: {
        status: 422,
        body: { status: 422, detail: "end_at can't come before start_at.", errors: [] },
      },
      [`DELETE ${EVENTS}/${event.id}`]: { status: 204, body: null },
    });
    const onOpenChange = vi.fn();
    renderWithProviders(
      <CalendarEventDialog calendarId={CAL_ID} event={event} open onOpenChange={onOpenChange} />,
    );
    expect(await screen.findByLabelText('Title')).toHaveValue('Release 2.0');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('before start_at');
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));
    await userEvent.click(within_dialog('Delete this event?'));
    expect(calls.map((c) => c.method)).toEqual(['PATCH', 'DELETE']);
  });

  it('is read only for an event you may not edit', async () => {
    mockFetch({});
    renderWithProviders(
      <CalendarEventDialog
        calendarId={CAL_ID}
        event={AGENDA.events[1]}
        open
        onOpenChange={vi.fn()}
      />,
    );
    expect(await screen.findByLabelText('Title')).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Save' })).not.toBeInTheDocument();
    expect(screen.getByText('Added by @ana')).toBeInTheDocument();
  });
});

function within_dialog(title: string): HTMLElement {
  const dialog = screen.getByRole('dialog', { name: title });
  const buttons = dialog.querySelectorAll('button');
  return [...buttons].find((b) => b.textContent === 'Delete') as HTMLElement;
}
