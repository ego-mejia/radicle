import { fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { ShortcutsContext } from '../../../../contexts/shortcuts';
import i18n from '../../../../i18n';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { GlobalShortcuts } from '.';

describe('GlobalShortcuts', () => {
  beforeEach(() => {
    void i18n.changeLanguage('en');
    mockFetch({ 'GET /api/v1/filters': { status: 200, body: { items: [], next_cursor: null } } });
  });

  it('opens help with ? but not while typing in a field', async () => {
    renderWithProviders(
      <>
        <input aria-label="Notes" />
        <GlobalShortcuts />
      </>,
    );
    const input = await screen.findByRole('textbox', { name: 'Notes' });
    await userEvent.type(input, '?');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    input.blur();
    fireEvent.keyDown(window, { key: '?' });
    expect(await screen.findByRole('dialog', { name: 'Keyboard shortcuts' })).toBeInTheDocument();
  });

  it('respects the preference to turn shortcuts off, but ⌘K still works', async () => {
    renderWithProviders(
      <ShortcutsContext.Provider value={false}>
        <GlobalShortcuts />
      </ShortcutsContext.Provider>,
    );
    await screen.findByText((_, el) => el?.tagName === 'BODY');
    fireEvent.keyDown(window, { key: '?' });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'k', metaKey: true });
    const input = await screen.findByRole('combobox');
    await userEvent.type(input, 'pa-12');
    expect(await screen.findByRole('option', { name: /Open PA-12/ })).toBeInTheDocument();
    await userEvent.clear(input);
    await userEvent.type(input, 'create');
    expect(await screen.findByRole('option', { name: /Create ticket/ })).toBeInTheDocument();
  });
});
