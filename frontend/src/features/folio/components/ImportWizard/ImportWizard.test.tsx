import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { ImportWizard } from '.';

const space = { key: 'eng', name: 'Ingeniería', kind: 'team', permissions: ['view', 'admin'] };
const plan = {
  pages: [
    {
      external_id: 'c:1',
      title: 'Home',
      kind: 'page',
      parent_id: null,
      action: 'create',
      author: 'Ana López',
      labels: [],
      attachments: 0,
      rows: 0,
      errors: [],
    },
    {
      external_id: 'c:2',
      title: 'Conectar un agente',
      kind: 'page',
      parent_id: 'c:1',
      action: 'update',
      author: 'Ana López',
      labels: ['mcp'],
      attachments: 3,
      rows: 0,
      errors: ['Missing file: x.png'],
    },
  ],
  authors: [{ source: 'Ana López', user: null }],
  errors: [],
  totals: { pages: 2, folders: 0, databases: 0, attachments: 3, updates: 1, with_errors: 1 },
};
const base = {
  id: 'i1',
  source: 'confluence',
  space: 'eng',
  filename: 'ENG.zip',
  options: {},
  stats: {},
  created_at: '2026-10-21T10:00:00Z',
  finished_at: null,
};

describe('ImportWizard', () => {
  it('uploads, shows the dry run, maps an author and runs the import', async () => {
    let state = { ...base, status: 'uploaded', report: {} };
    const calls = mockFetch({
      'GET /api/v1/folio/spaces': { status: 200, body: { items: [space] } },
      'GET /api/v1/folio/imports': () => ({ status: 200, body: { items: [] } }),
      'GET /api/v1/folio/people': {
        status: 200,
        body: { items: [{ handle: 'ana', name: 'Ana', kind: 'human' }] },
      },
      'GET /api/v1/folio/metadata-schema': {
        status: 200,
        body: {
          doc_types: [{ key: 'how-to', name: 'How-to' }],
          audiences: [],
          languages: [],
          fields: [],
        },
      },
      'POST /api/v1/folio/imports': () => ({ status: 201, body: state }),
      'POST /api/v1/folio/imports/i1/dry-run': () => {
        state = { ...state, status: 'checked', report: plan };
        return { status: 200, body: state };
      },
      'POST /api/v1/folio/imports/i1/run': () => {
        state = {
          ...state,
          status: 'done',
          stats: { created: 1, updated: 1, published: 0, drafts: 2, failed: 0 },
          report: {
            ...plan,
            run: [
              {
                external_id: 'c:1',
                title: 'Home',
                action: 'created',
                node_id: 'n1',
                published: false,
                errors: [],
              },
            ],
          },
        };
        return { status: 202, body: state };
      },
      'GET /api/v1/folio/imports/i1': () => ({ status: 200, body: state }),
    });
    renderWithProviders(<ImportWizard />);
    const file = new File(['zip'], 'ENG.zip', { type: 'application/zip' });
    await userEvent.upload(await screen.findByLabelText('Export file'), file);
    await waitFor(() =>
      expect(screen.getByRole('option', { name: 'Ingeniería' })).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Upload and check' }));
    expect(await screen.findByText('Conectar un agente')).toBeInTheDocument();
    expect(screen.getByText('Missing file: x.png')).toBeInTheDocument();
    expect(screen.getByText('Update')).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole('option', { name: 'Ana (@ana)' })).toBeInTheDocument(),
    );
    await userEvent.selectOptions(screen.getByLabelText('Who Ana López becomes'), 'ana');
    await userEvent.click(screen.getByRole('button', { name: 'Import 2 pages' }));
    expect(await screen.findByText('Imported')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/folio/p/n1');
    const sent = calls.filter((c) => c.path === '/api/v1/folio/imports/i1/dry-run');
    expect(sent.at(-1)?.body).toEqual({ authors: { 'Ana López': 'ana' }, default_metadata: null });
    const upload = calls.find((c) => c.method === 'POST' && c.path === '/api/v1/folio/imports');
    expect(upload).toBeDefined();
  });

  it('says why an upload is refused', async () => {
    mockFetch({
      'GET /api/v1/folio/spaces': { status: 200, body: { items: [space] } },
      'GET /api/v1/folio/imports': { status: 200, body: { items: [] } },
      'POST /api/v1/folio/imports': {
        status: 422,
        body: { status: 422, detail: 'The zip has no files to import.', errors: [] },
      },
    });
    renderWithProviders(<ImportWizard />);
    await userEvent.upload(await screen.findByLabelText('Export file'), new File(['x'], 'a.zip'));
    await waitFor(() =>
      expect(screen.getByRole('option', { name: 'Ingeniería' })).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByRole('button', { name: 'Upload and check' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The zip has no files to import.');
  });
});
