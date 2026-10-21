import type { NodeViewProps } from '@tiptap/react';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { AGENDA, CAL_ID, CALENDAR } from '../../calendar/fixtures';
import { toFolioDoc } from '../../editor/schema';
import { DocContent } from '../DocContent';
import { CalendarBlock } from '.';

function block(attrs: { calendar: string | null; view?: string | null }, selected = false) {
  const updateAttributes = vi.fn();
  const props = { node: { attrs }, updateAttributes, selected } as unknown as NodeViewProps;
  renderWithProviders(<CalendarBlock {...props} />);
  return updateAttributes;
}

describe('CalendarBlock', () => {
  it('asks which calendar and view, from every space the author can see', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/calendars': { status: 200, body: { items: [CALENDAR] } },
    });
    const update = block({ calendar: null });
    const picker = await screen.findByRole('combobox', { name: 'Choose a calendar' });
    await screen.findByRole('option', { name: 'Releases · eng' });
    await userEvent.selectOptions(picker, 'Releases · eng');
    expect(update).toHaveBeenCalledWith({ calendar: CAL_ID });
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'View' }), 'Week');
    expect(update).toHaveBeenCalledWith({ view: 'week' });
    expect(calls[0]?.path).toBe('/api/v1/folio/calendars');
  });

  it('is saved only once it names a calendar', () => {
    const doc = {
      type: 'doc',
      content: [
        { type: 'calendar', attrs: { calendar: null, view: null } },
        { type: 'calendar', attrs: { calendar: CAL_ID, view: 'week' } },
      ],
    };
    expect(toFolioDoc(doc).content).toEqual([
      { type: 'calendar', attrs: { calendar: CAL_ID, view: 'week' } },
    ]);
  });
});

describe('the calendar block for readers', () => {
  const doc = { type: 'doc', content: [{ type: 'calendar', attrs: { calendar: CAL_ID } }] };

  it('shows the calendar with a link to the space calendars', async () => {
    mockFetch({
      [`GET /api/v1/folio/calendars/${CAL_ID}`]: { status: 200, body: CALENDAR },
      [`GET /api/v1/folio/calendars/${CAL_ID}/events`]: { status: 200, body: AGENDA },
    });
    renderWithProviders(<DocContent doc={doc} />);
    expect(await screen.findByRole('region', { name: 'Releases' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: "Open the space's calendars" })).toBeInTheDocument();
  });

  it('without access shows a placeholder', async () => {
    mockFetch({});
    renderWithProviders(<DocContent doc={doc} />);
    expect(await screen.findByRole('note')).toHaveTextContent("You can't see this calendar.");
  });
});
