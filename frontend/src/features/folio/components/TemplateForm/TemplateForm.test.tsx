import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SPEC } from '../TemplatePicker/fixtures';
import { TemplateForm } from '.';

// TipTap needs layout APIs jsdom lacks; the form's job is to save what the body reports.
vi.mock('../TemplateBody', () => ({
  TemplateBody: ({
    content,
    onChange,
  }: {
    content: unknown;
    onChange: (doc: Record<string, unknown>) => void;
  }) => (
    <div>
      <p>{JSON.stringify(content).includes('Entregables') ? 'Entregables' : ''}</p>
      <button type="button" onClick={() => onChange({ type: 'doc', content: [] })}>
        write
      </button>
    </div>
  ),
}));

const SCHEMA = {
  fields: [],
  doc_types: [
    { key: 'build-spec', name: 'Build spec', description: '', position: 0, active: true },
  ],
  audiences: [],
  languages: [],
};

describe('TemplateForm', () => {
  it('saves the name, document type and labels of a page template', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/metadata-schema': { status: 200, body: SCHEMA },
      'PATCH /api/v1/folio/templates/t1': (_req, body) => ({
        status: 200,
        body: { ...SPEC, ...(body as object) },
      }),
    });
    renderWithProviders(
      <TemplateForm template={{ ...SPEC, default_metadata: { labels: ['spec'] } }} />,
    );
    expect(await screen.findByText('Entregables')).toBeInTheDocument();
    expect(screen.getByText(/Variables: \{\{date\}\}, \{\{author\}\}/)).toBeInTheDocument();
    const name = screen.getByLabelText('Name');
    await userEvent.clear(name);
    await userEvent.type(name, 'Spec de etapa');
    await userEvent.type(screen.getByLabelText('Default labels'), ', #Etapa');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    await vi.waitFor(() =>
      expect(calls.find((c) => c.method === 'PATCH')?.body).toMatchObject({
        name: 'Spec de etapa',
        doc_type_key: 'build-spec',
        default_metadata: { labels: ['spec', 'etapa'] },
        structure: null,
      }),
    );
  });

  it('says when a space template structure is not JSON', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/metadata-schema': { status: 200, body: SCHEMA },
    });
    renderWithProviders(
      <TemplateForm
        template={{ ...SPEC, kind: 'space', content_json: null, structure: { pages: [] } }}
      />,
    );
    const structure = await screen.findByLabelText('Structure');
    await userEvent.clear(structure);
    await userEvent.type(structure, 'no es json');
    await userEvent.click(screen.getByRole('button', { name: 'Save' }));
    expect(await screen.findByText('That is not valid JSON.')).toBeInTheDocument();
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false);
  });

  it('saves what you write in the body with the rest of the form', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/metadata-schema': { status: 200, body: SCHEMA },
      'PATCH /api/v1/folio/templates/t1': (_req, body) => ({
        status: 200,
        body: { ...SPEC, ...(body as object) },
      }),
    });
    renderWithProviders(<TemplateForm template={SPEC} />);
    await userEvent.click(await screen.findByRole('button', { name: 'write' }));
    await vi.waitFor(
      () =>
        expect(calls.find((c) => c.method === 'PATCH')?.body).toMatchObject({
          name: 'Build spec',
          doc_type_key: 'build-spec',
          content_json: { type: 'doc', content: [] },
        }),
      { timeout: 4000 },
    );
    expect(await screen.findByText('Saved')).toBeInTheDocument();
  });
});
