import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { authKeys } from '../../../../services/api/auth';
import {
  ME,
  makeClient,
  mockFetch,
  renderWithProviders,
} from '../../../../test/renderWithProviders';
import { PublishDialog } from '.';

const ID = '9f3c0000-0000-4000-8000-000000000001';
const entry = (key: string, name: string) => ({
  key,
  name,
  description: '',
  position: 0,
  active: true,
});
const SCHEMA = {
  fields: [],
  doc_types: [entry('how-to', 'How-to')],
  audiences: [entry('everyone', 'Everyone'), entry('eng', 'Engineering')],
  languages: [entry('es', 'Español')],
};
const METADATA = {
  description: 'Cómo conectar un agente a Radicle por MCP, paso a paso y con el token.',
  doc_type: 'how-to',
  labels: ['mcp', 'agentes'],
  owner: 'fernando',
  audiences: ['everyone'],
  language: 'es',
};
const draft = (metadata: object) => ({
  content_json: { type: 'doc' },
  content_md: '',
  metadata,
  saved: true,
  updated_at: null,
});

function setup(metadata: object, publish: Parameters<typeof mockFetch>[0][string]) {
  const calls = mockFetch({
    'GET /api/v1/folio/metadata-schema': { status: 200, body: SCHEMA },
    [`GET /api/v1/folio/nodes/${ID}/draft`]: { status: 200, body: draft(metadata) },
    [`PUT /api/v1/folio/nodes/${ID}/draft`]: (_r, body) => ({
      status: 200,
      body: draft((body as { metadata: object }).metadata),
    }),
    [`POST /api/v1/folio/nodes/${ID}/publish`]: publish,
  });
  return calls;
}

describe('PublishDialog', () => {
  it('publishes the draft with its metadata and a change note', async () => {
    const version = { number: 2, title: 'Guía', author: 'luis', metadata: METADATA };
    const calls = setup(METADATA, { status: 201, body: version });
    const onPublished = vi.fn();
    renderWithProviders(
      <PublishDialog
        nodeId={ID}
        title="Guía"
        open
        onOpenChange={() => undefined}
        onPublished={onPublished}
      />,
    );
    expect(await screen.findByDisplayValue('mcp, agentes')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Change note'), 'Paso del token');
    await userEvent.click(screen.getByRole('button', { name: 'Publish' }));
    await waitFor(() => expect(onPublished).toHaveBeenCalledWith(version));
    const sent = calls.filter((c) => c.method !== 'GET').map((c) => [c.method, c.body]);
    expect(sent).toEqual([
      ['PUT', { metadata: METADATA }],
      ['POST', { change_note: 'Paso del token', confirm: false }],
    ]);
  });

  it('checks the fields as you go and shows the server errors on them', async () => {
    const problem = {
      status: 422,
      detail: 'Complete the metadata',
      errors: [{ field: 'owner', message: 'an active person who can read Folio' }],
    };
    const calls = setup({ ...METADATA, description: '' }, { status: 422, body: problem });
    renderWithProviders(
      <PublishDialog
        nodeId={ID}
        title="Guía"
        open
        onOpenChange={() => undefined}
        onPublished={vi.fn()}
      />,
    );
    const description = await screen.findByLabelText('Description');
    await userEvent.type(description, 'Muy corta.');
    await userEvent.tab();
    expect(screen.getByText('40 to 400 characters.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Publish' }));
    expect(calls.some((c) => c.method === 'POST')).toBe(false);

    await userEvent.clear(description);
    await userEvent.type(description, METADATA.description);
    await userEvent.click(screen.getByRole('button', { name: 'Publish' }));
    expect(await screen.findByText('an active person who can read Folio')).toBeInTheDocument();
  });

  it('agents send it for approval', async () => {
    const submission = { id: 's1', node_id: ID, title: 'Guía', status: 'pending' };
    setup(METADATA, { status: 202, body: submission });
    const client = makeClient();
    client.setQueryData(authKeys.me, { ...ME, kind: 'agent' });
    const onPublished = vi.fn();
    renderWithProviders(
      <PublishDialog
        nodeId={ID}
        title="Guía"
        open
        onOpenChange={() => undefined}
        onPublished={onPublished}
      />,
      client,
    );
    expect(await screen.findByText(/reviews it before it goes live/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Send for approval' }));
    await waitFor(() => expect(onPublished).toHaveBeenCalledWith(submission));
  });
});
