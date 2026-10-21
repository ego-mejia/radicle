import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { DB_ID, dbApi } from '../DatabaseView/fixtures';
import { NewNodeDialog } from '../NewNodeDialog';
import { ReadPage } from '../ReadPage';

const NODE = {
  id: DB_ID,
  kind: 'database',
  title: 'Inventario',
  slug: 'inventario',
  icon: null,
  space: 'ai-tools',
  parent_id: null,
  cover_asset_id: null,
  published_at: null,
  created_at: '2026-10-21T10:00:00Z',
  updated_at: '2026-10-21T10:00:00Z',
  breadcrumbs: [],
  version: null,
  status: 'draft',
  verified_until: null,
  can_edit: true,
  can_delete: true,
  archived_at: null,
  metadata: {},
  content_json: null,
};

describe('DatabasePage', () => {
  it('opens a database node on its views, never asking for a draft', async () => {
    const calls = dbApi(undefined, {
      [`GET /api/v1/folio/nodes/${DB_ID}`]: { status: 200, body: NODE },
      'GET /api/v1/folio/spaces/ai-tools': {
        status: 200,
        body: { key: 'ai-tools', name: 'AI Tools', permissions: ['view'] },
      },
    });
    renderWithProviders(<ReadPage nodeId={DB_ID} />);
    expect(await screen.findByRole('heading', { name: 'Inventario' })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'AI Tools' })).toBeInTheDocument();
    expect(await screen.findByRole('table')).toBeInTheDocument();
    expect(calls.some((c) => c.path.endsWith('/draft'))).toBe(false);
  });

  it('creates a database without templates', async () => {
    const calls = dbApi(undefined, {
      'POST /api/v1/folio/nodes': { status: 201, body: NODE },
    });
    renderWithProviders(
      <NewNodeDialog space="ai-tools" kind="database" open onOpenChange={() => {}} />,
    );
    expect(await screen.findByRole('dialog', { name: 'New database' })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Title'), 'Inventario');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
        space: 'ai-tools',
        kind: 'database',
        title: 'Inventario',
        parent: null,
      }),
    );
    expect(calls.some((c) => c.path.includes('/templates'))).toBe(false);
  });
});
