import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SubmissionReview } from '.';

const para = (text: string) => ({ type: 'paragraph', content: [{ type: 'text', text }] });
const detail = {
  id: 's1',
  node_id: 'n1',
  title: 'Cambios de la semana',
  status: 'pending',
  change_note: 'Desde el README',
  submitted_by: 'agente-docs',
  reviewed_by: null,
  review_comment: null,
  version: null,
  created_at: '2026-10-20T10:00:00Z',
  decided_at: null,
  metadata: { doc_type: 'how-to', labels: ['mcp'] },
  content_json: { type: 'doc', content: [para('Hola')] },
  content_md: 'Hola',
  current_version: null,
  changes: [],
  blocks: [{ op: 'added', block: para('Hola') }],
};

function setup(canDecide: boolean, handlers = {}) {
  const calls = mockFetch({
    'GET /api/v1/folio/submissions/s1': { status: 200, body: detail },
    ...handlers,
  });
  renderWithProviders(<SubmissionReview id="s1" canDecide={canDecide} />);
  return calls;
}

describe('SubmissionReview', () => {
  it('shows the diff and a preview, and approves', async () => {
    const calls = setup(true, {
      'POST /api/v1/folio/submissions/s1/approve': { status: 201, body: { number: 1 } },
    });
    const panel = await screen.findByRole('region', { name: 'Cambios de la semana' });
    expect(within(panel).getByLabelText('Added')).toHaveTextContent('Hola');
    expect(within(panel).getByText('how-to')).toBeInTheDocument();
    expect(within(panel).getByText('Desde el README')).toBeInTheDocument();
    await userEvent.click(within(panel).getByRole('tab', { name: 'Preview' }));
    expect(within(panel).queryByLabelText('Added')).not.toBeInTheDocument();
    expect(within(panel).getByText('Hola')).toBeInTheDocument();
    await userEvent.click(within(panel).getByRole('button', { name: 'Approve' }));
    await waitFor(() => expect(calls.some((c) => c.path.endsWith('/s1/approve'))).toBe(true));
  });

  it('asks for a comment to reject and shows the problem', async () => {
    const calls = setup(true, {
      'POST /api/v1/folio/submissions/s1/reject': {
        status: 409,
        body: { status: 409, detail: 'Someone already decided it.', errors: [] },
      },
    });
    const panel = await screen.findByRole('region', { name: 'Cambios de la semana' });
    await userEvent.click(within(panel).getByRole('button', { name: 'Reject' }));
    const dialog = await screen.findByRole('dialog');
    const send = within(dialog).getByRole('button', { name: 'Reject' });
    expect(send).toBeDisabled();
    await userEvent.type(within(dialog).getByRole('textbox'), 'Falta el diagrama.');
    await userEvent.click(send);
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('already decided');
    expect(calls.find((c) => c.path.endsWith('/reject'))?.body).toEqual({
      comment: 'Falta el diagrama.',
    });
  });

  it('has no decisions for people who cannot decide', async () => {
    setup(false);
    const panel = await screen.findByRole('region', { name: 'Cambios de la semana' });
    expect(within(panel).queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument();
  });
});
