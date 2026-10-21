import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../../../test/renderWithProviders';
import { PublishDialog } from '../..';

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
  audiences: [entry('everyone', 'Everyone')],
  languages: [entry('es', 'Español')],
};
const SUGGESTION = {
  description: 'Cómo crear un agente en Admin y conectarlo a Radicle por MCP con su token.',
  labels: ['mcp', 'agentes'],
  doc_type: 'how-to',
};
const draft = (metadata: object) => ({
  content_json: { type: 'doc' },
  content_md: '',
  metadata,
  saved: true,
  updated_at: null,
});

function setup(metadata: object, available = true) {
  return mockFetch({
    'GET /api/v1/folio/metadata-schema': { status: 200, body: SCHEMA },
    [`GET /api/v1/folio/nodes/${ID}/draft`]: { status: 200, body: draft(metadata) },
    'GET /api/v1/folio/ai/availability': {
      status: 200,
      body: { available, reason: available ? null : 'no_provider', message: null },
    },
    'POST /api/v1/folio/ai/suggest-metadata': { status: 200, body: SUGGESTION },
  });
}

const dialog = () => (
  <PublishDialog
    nodeId={ID}
    title="Guía"
    space="docs"
    open
    onOpenChange={() => undefined}
    onPublished={vi.fn()}
  />
);

describe('AiSuggestions', () => {
  it('proposes the empty fields and fills only the ones you accept', async () => {
    const calls = setup({ doc_type: 'how-to' });
    renderWithProviders(dialog());
    const box = await screen.findByRole('region', { name: 'AI suggestions' });
    expect(box).toHaveTextContent(SUGGESTION.description);
    expect(box).toHaveTextContent('mcp, agentes');
    expect(box).not.toHaveTextContent('How-to'); // the type was already chosen
    expect(screen.getByLabelText('Description')).toHaveValue('');

    await userEvent.click(screen.getByRole('button', { name: 'Use the suggested Description' }));
    expect(screen.getByLabelText('Description')).toHaveValue(SUGGESTION.description);
    expect(screen.getByRole('region', { name: 'AI suggestions' })).not.toHaveTextContent(
      SUGGESTION.description,
    );
    await userEvent.click(screen.getByRole('button', { name: 'Use the suggested Labels' }));
    expect(await screen.findByDisplayValue('mcp, agentes')).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'AI suggestions' })).toBeNull();
    expect(calls.some((c) => c.path.endsWith('/publish'))).toBe(false); // never publishes
  });

  it('asks nothing when the fields are filled or the AI is off', async () => {
    const full = { description: SUGGESTION.description, labels: ['mcp'], doc_type: 'how-to' };
    const calls = setup(full);
    const { unmount } = renderWithProviders(dialog());
    expect(await screen.findByLabelText('Description')).toHaveValue(SUGGESTION.description);
    unmount();
    const off = setup({}, false);
    renderWithProviders(dialog());
    await screen.findByLabelText('Description');
    await waitFor(() => expect(off.some((c) => c.path.includes('availability'))).toBe(true));
    expect(screen.queryByRole('region', { name: 'AI suggestions' })).toBeNull();
    expect([...calls, ...off].some((c) => c.path.endsWith('/suggest-metadata'))).toBe(false);
  });
});
