import { fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { ShareDialog } from '.';

const URL = 'POST /api/v1/folio/nodes/n1/share';

describe('ShareDialog', () => {
  it('sends to people and groups and says who can not see it', async () => {
    const calls = mockFetch({
      [URL]: {
        status: 200,
        body: { notified: ['ana'], cannot_see: ['luis'], granted: [] },
      },
    });
    renderWithProviders(<ShareDialog nodeId="n1" title="Deploy" open onOpenChange={() => {}} />);
    const send = await screen.findByRole('button', { name: 'Send' });
    expect(send).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/^People/), { target: { value: '@ana, luis' } });
    fireEvent.change(screen.getByLabelText('Groups'), { target: { value: 'equipo' } });
    fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'Léela' } });
    fireEvent.click(send);
    expect(await screen.findByText('Sent to @ana.')).toBeInTheDocument();
    expect(screen.getByText(/@luis can't see this page/)).toBeInTheDocument();
    await waitFor(() =>
      expect(calls[0]?.body).toEqual({
        users: ['@ana', 'luis'],
        groups: ['equipo'],
        message: 'Léela',
        grant_view: false,
      }),
    );
  });

  it("shows the server's reason when it can't let them in", async () => {
    mockFetch({
      [URL]: {
        status: 403,
        body: { status: 403, detail: 'Ask someone who can edit the restricted page.', errors: [] },
      },
    });
    renderWithProviders(<ShareDialog nodeId="n1" title="Deploy" open onOpenChange={() => {}} />);
    fireEvent.change(await screen.findByLabelText(/^People/), { target: { value: 'luis' } });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Ask someone who can edit');
  });
});
