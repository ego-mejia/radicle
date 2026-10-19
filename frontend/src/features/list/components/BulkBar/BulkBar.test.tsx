import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../../../i18n';
import { PROJECT } from '../../../../test/fixtures';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { BulkBar } from '.';

describe('BulkBar', () => {
  beforeEach(() => i18n.changeLanguage('en'));

  it('previews with a dry run, then applies', async () => {
    const calls = mockFetch({
      'POST /api/v1/tickets/bulk': (_req, body) => {
        const dry = (body as { dry_run: boolean }).dry_run;
        return {
          status: 200,
          body: {
            total: 2,
            dry_run: dry,
            succeeded: 1,
            failed: 1,
            results: [
              { key: 'PA-1', ok: true, error: null },
              { key: 'PA-2', ok: false, error: 'Transition not allowed' },
            ],
            job: null,
          },
        };
      },
    });
    const onDone = vi.fn();
    renderWithProviders(
      <BulkBar
        project={PROJECT}
        keys={['PA-1', 'PA-2']}
        onClear={() => undefined}
        onDone={onDone}
      />,
    );
    await userEvent.click(await screen.findByRole('button', { name: 'Tags' }));
    await userEvent.type(screen.getByRole('textbox', { name: 'Tag' }), 'backlog');
    await userEvent.click(screen.getByRole('button', { name: 'Preview' }));
    expect(await screen.findByText('1 would change, 1 would fail:')).toBeInTheDocument();
    expect(screen.getByText('Transition not allowed')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Apply to 1 ticket' }));
    await waitFor(() => expect(calls.filter((c) => c.method === 'POST')).toHaveLength(2));
    expect(calls[0]!.body).toMatchObject({
      keys: ['PA-1', 'PA-2'],
      operations: [{ op: 'remove_tag', tag: 'backlog' }],
      dry_run: true,
    });
    expect(calls[1]!.body).toMatchObject({ dry_run: false });
    expect(await screen.findByText('1 changed, 1 failed.')).toBeInTheDocument();
  });
});
