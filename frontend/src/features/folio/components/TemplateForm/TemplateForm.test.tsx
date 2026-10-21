import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SPEC } from '../TemplatePicker/fixtures';
import { TemplateForm } from '.';

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
    expect(await screen.findByRole('region', { name: 'Template content' })).toHaveTextContent(
      'Entregables',
    );
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
});
