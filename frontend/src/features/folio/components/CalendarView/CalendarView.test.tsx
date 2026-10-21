import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { AGENDA, CAL_ID, CALENDAR } from '../../calendar/fixtures';
import { CalendarView } from '.';

const DECEMBER = new Date(2026, 11, 10);

function agendaMock() {
  return mockFetch({
    [`GET /api/v1/folio/calendars/${CAL_ID}/events`]: { status: 200, body: AGENDA },
  });
}

describe('CalendarView', () => {
  it('shows the month with events by category and the Docket milestones', async () => {
    const calls = agendaMock();
    renderWithProviders(<CalendarView calendar={CALENDAR} initial={DECEMBER} />);
    expect(await screen.findByText('Release 2.0')).toBeInTheDocument();
    const day15 = document.querySelector('[data-day="2026-12-15"]') as HTMLElement;
    expect(within(day15).getByText(/PA · V1/)).toBeInTheDocument();
    expect(within(day15).getByText('Vacaciones de Ana')).toBeInTheDocument();
    const day14 = document.querySelector('[data-day="2026-12-14"]') as HTMLElement;
    expect(within(day14).getByText('Vacaciones de Ana')).toBeInTheDocument();
    expect(document.querySelector('[data-day="2026-12-16"]')?.textContent).not.toContain(
      'Vacaciones',
    );
    expect(screen.getByText('Docket milestone')).toBeInTheDocument();
    expect(decodeURIComponent(calls[0]?.path ?? '')).toContain('start=');
  });

  it('moves between months and switches to the week', async () => {
    const calls = agendaMock();
    const onModeChange = vi.fn();
    renderWithProviders(
      <CalendarView calendar={CALENDAR} initial={DECEMBER} onModeChange={onModeChange} />,
    );
    await screen.findByText('Release 2.0');
    await userEvent.click(screen.getByRole('button', { name: 'Next month' }));
    expect(await screen.findByRole('heading', { name: /January/i })).toBeInTheDocument();
    expect(calls.length).toBe(2);
    await userEvent.click(screen.getByRole('button', { name: 'Week' }));
    expect(onModeChange).toHaveBeenCalledWith('week');
  });

  it('opens an event when asked, and shows seven days in week mode', async () => {
    agendaMock();
    const onSelect = vi.fn();
    renderWithProviders(
      <CalendarView calendar={CALENDAR} initial={DECEMBER} mode="week" onSelectEvent={onSelect} />,
    );
    await userEvent.click(await screen.findByRole('button', { name: /Release 2.0/ }));
    expect(onSelect).toHaveBeenCalledWith(AGENDA.events[0]);
    expect(document.querySelectorAll('[data-day]')).toHaveLength(7);
  });
});
