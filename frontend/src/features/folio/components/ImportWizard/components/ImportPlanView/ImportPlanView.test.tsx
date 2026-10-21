import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../../../test/renderWithProviders';
import type { FolioImport } from '../../../../../../services/api/folioImports';
import { ImportPlanView } from '.';

const page = (id: string, title: string, extra: object = {}) => ({
  external_id: id,
  title,
  kind: 'page',
  parent_id: null,
  action: 'create',
  author: 'Ana López',
  labels: [],
  attachments: 0,
  rows: 0,
  errors: [],
  ...extra,
});
const item = {
  id: 'i1',
  source: 'notion',
  space: 'eng',
  filename: 'n.zip',
  status: 'checked',
  options: {},
  stats: {},
  created_at: '2026-10-21T10:00:00Z',
  finished_at: null,
  report: {
    pages: [
      page('n:1', 'Ingenieria'),
      page('n:2', 'Conectar un agente', {
        parent_id: 'n:1',
        action: 'update',
        labels: ['mcp', 'agents'],
        attachments: 2,
        errors: ['Missing file: x.png'],
      }),
      page('n:3', 'AI Tools', { kind: 'database', rows: 12 }),
    ],
    authors: [{ source: 'Ana López', user: { id: 'u1', handle: 'ana', name: 'Ana' } }],
    errors: ['Something about the zip.'],
    totals: { pages: 2, folders: 0, databases: 1, attachments: 2, updates: 1, with_errors: 1 },
  },
} as unknown as FolioImport;

function mocks(onRun: () => void = () => {}) {
  return mockFetch({
    'GET /api/v1/folio/people': {
      status: 200,
      body: {
        items: [
          { handle: 'ana', name: 'Ana', kind: 'human' },
          { handle: 'luis', name: 'Luis', kind: 'human' },
        ],
      },
    },
    'GET /api/v1/folio/metadata-schema': {
      status: 200,
      body: {
        doc_types: [{ key: 'how-to', name: 'How-to' }],
        audiences: [{ key: 'everyone', name: 'Everyone' }],
        languages: [{ key: 'es', name: 'Español' }],
        fields: [],
      },
    },
    'POST /api/v1/folio/imports/i1/dry-run': { status: 200, body: item },
    'POST /api/v1/folio/imports/i1/run': () => {
      onRun();
      return { status: 202, body: { ...item, status: 'running' } };
    },
  });
}

describe('ImportPlanView', () => {
  it('shows every page with what will happen and its problems', async () => {
    mocks();
    renderWithProviders(<ImportPlanView item={item} onChange={vi.fn()} />);
    expect(await screen.findByText('Something about the zip.')).toBeInTheDocument();
    expect(screen.getByText('Missing file: x.png')).toBeInTheDocument();
    expect(screen.getByText('Update')).toBeInTheDocument();
    expect(screen.getByText('mcp, agents')).toBeInTheDocument();
    expect(screen.getByText('12 rows')).toBeInTheDocument();
    expect(screen.getByText('already imported').previousSibling).toHaveTextContent('1');
    await waitFor(() => expect(screen.getByLabelText('Who Ana López becomes')).toHaveValue('ana'));
  });

  it('checks again with the chosen people and metadata, then runs', async () => {
    let ran = false;
    const calls = mocks(() => {
      ran = true;
    });
    const onChange = vi.fn();
    renderWithProviders(<ImportPlanView item={item} onChange={onChange} />);
    await waitFor(() =>
      expect(screen.getByRole('option', { name: 'Luis (@luis)' })).toBeInTheDocument(),
    );
    await userEvent.selectOptions(screen.getByLabelText('Who Ana López becomes'), 'luis');
    await waitFor(() => expect(screen.getByRole('option', { name: 'How-to' })).toBeInTheDocument());
    await userEvent.selectOptions(screen.getByLabelText('Type'), 'how-to');
    await userEvent.selectOptions(screen.getByLabelText('For'), 'everyone');
    await userEvent.click(screen.getByRole('button', { name: 'Check again' }));
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(item));
    const sent = calls.find((c) => c.path === '/api/v1/folio/imports/i1/dry-run');
    expect(sent?.body).toEqual({
      authors: { 'Ana López': 'luis' },
      default_metadata: { doc_type: 'how-to', audiences: ['everyone'] },
    });
    await userEvent.click(screen.getByRole('button', { name: 'Import 3 pages' }));
    await waitFor(() => expect(ran).toBe(true));
  });
});
