import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { GlossaryAdmin } from '.';

const term = (id: string, name: string, status: string) => ({
  id,
  term: name,
  aliases: [],
  definition: `${name} es parte de Radicle.`,
  status,
  source: null,
  updated_at: '2026-10-21T10:00:00Z',
});

describe('GlossaryAdmin', () => {
  it('approves suggestions, asks the AI for more and adds a term by hand', async () => {
    let suggested = [term('s1', 'Docket', 'suggested')];
    const calls = mockFetch({
      'GET /api/v1/folio/glossary': (req) =>
        new URL(req.url).searchParams.get('status') === 'suggested'
          ? { status: 200, body: { items: suggested } }
          : { status: 200, body: { items: [term('a1', 'Folio', 'approved')] } },
      'PATCH /api/v1/folio/glossary/s1': () => {
        suggested = [];
        return { status: 200, body: term('s1', 'Docket', 'approved') };
      },
      'POST /api/v1/folio/glossary/suggestions': {
        status: 201,
        body: { items: [term('s2', 'RQL', 'suggested')] },
      },
      'POST /api/v1/folio/glossary': (_r, body) => ({
        status: 201,
        body: { ...term('a2', 'MCP', 'approved'), ...(body as object) },
      }),
    });
    renderWithProviders(<GlossaryAdmin />);
    expect(await screen.findByText('Folio es parte de Radicle.')).toBeInTheDocument();
    await userEvent.click(await screen.findByRole('button', { name: 'Approve Docket' }));
    await waitFor(() => expect(screen.getByText('No suggestions waiting.')).toBeInTheDocument());
    expect(calls.find((c) => c.method === 'PATCH')?.body).toEqual({ status: 'approved' });

    await userEvent.click(screen.getByRole('button', { name: 'Suggest from Verified docs' }));
    expect(await screen.findByText('1 new suggestion')).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText('Term'), 'MCP');
    await userEvent.type(screen.getByLabelText(/^Aliases/), 'protocolo, model context');
    await userEvent.type(screen.getByLabelText('Definition'), 'Cómo se conectan los agentes.');
    await userEvent.click(screen.getByRole('button', { name: 'Add term' }));
    expect(await screen.findByText('Term added')).toBeInTheDocument();
    expect(
      calls.find((c) => c.method === 'POST' && c.path === '/api/v1/folio/glossary')?.body,
    ).toEqual({
      term: 'MCP',
      definition: 'Cómo se conectan los agentes.',
      aliases: ['protocolo', 'model context'],
    });
  });

  it('shows the API error when suggesting fails', async () => {
    mockFetch({
      'GET /api/v1/folio/glossary': { status: 200, body: { items: [] } },
      'POST /api/v1/folio/glossary/suggestions': {
        status: 422,
        body: { status: 422, detail: 'There are no Verified docs yet', errors: [] },
      },
    });
    renderWithProviders(<GlossaryAdmin />);
    await userEvent.click(
      await screen.findByRole('button', { name: 'Suggest from Verified docs' }),
    );
    expect(await screen.findByText('There are no Verified docs yet')).toBeInTheDocument();
  });
});
