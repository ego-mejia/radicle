import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { NotificationPreferences } from '.';

const PREFS = (emailAvailable: boolean, inApp = true) => ({
  email_available: emailAvailable,
  items: [
    {
      app: 'folio',
      type: 'comment_mention',
      label: 'You were mentioned',
      in_app: inApp,
      email: true,
    },
  ],
});

describe('NotificationPreferences', () => {
  it('turns a channel off for one type', async () => {
    const calls = mockFetch({
      'GET /api/v1/me/notification-preferences': { status: 200, body: PREFS(true) },
      'PUT /api/v1/me/notification-preferences': { status: 200, body: PREFS(true, false) },
    });
    renderWithProviders(<NotificationPreferences />);
    const inApp = await screen.findByRole('checkbox', { name: 'In the app: Mentions in comments' });
    expect(inApp).toBeChecked();
    fireEvent.click(inApp);
    await waitFor(() => expect(inApp).not.toBeChecked());
    expect(calls.find((c) => c.method === 'PUT')?.body).toEqual({
      app: 'folio',
      type: 'comment_mention',
      channel: 'in_app',
      enabled: false,
    });
  });

  it('disables email and says why when SMTP is off', async () => {
    mockFetch({ 'GET /api/v1/me/notification-preferences': { status: 200, body: PREFS(false) } });
    renderWithProviders(<NotificationPreferences />);
    const email = await screen.findByRole('checkbox', { name: 'By email: Mentions in comments' });
    expect(email).toBeDisabled();
    expect(email).not.toBeChecked();
    expect(screen.getByText(/Email is off/)).toBeInTheDocument();
  });

  it("shows the server's label for a type it has no translation for", async () => {
    const body = PREFS(true);
    body.items.push({
      app: 'folio',
      type: 'brand_new',
      label: 'Something new happens',
      in_app: true,
      email: true,
    });
    mockFetch({ 'GET /api/v1/me/notification-preferences': { status: 200, body } });
    renderWithProviders(<NotificationPreferences />);
    expect(await screen.findByText('Mentions in comments')).toBeInTheDocument();
    expect(screen.getByText('Something new happens')).toBeInTheDocument();
  });
});
