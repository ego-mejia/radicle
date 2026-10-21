import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { FolioNode } from '../../../../services/api/folio';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { PageQuality } from '.';

const NODE = {
  id: 'n1',
  kind: 'page',
  title: 'Guía',
  slug: 'guia',
  icon: null,
  space: 'docs',
  parent_id: null,
  cover_asset_id: null,
  published_at: '2026-10-20T10:00:00Z',
  created_at: '2026-10-19T10:00:00Z',
  updated_at: '2026-10-20T10:00:00Z',
  breadcrumbs: [],
  version: 1,
  metadata: { owner: 'luis' },
  content_json: null,
  status: 'published',
  verified_until: null,
  archived_at: null,
  can_edit: true,
  can_delete: true,
} as FolioNode;

describe('PageQuality', () => {
  it('verifies the page and shows until when', async () => {
    mockFetch({
      'PATCH /api/v1/folio/nodes/n1/status': {
        status: 200,
        body: { ...NODE, status: 'verified', verified_until: '2027-01-18' },
      },
    });
    renderWithProviders(<PageQuality node={NODE} canManage />);
    await userEvent.click(await screen.findByRole('button', { name: 'Verify' }));
    expect(await screen.findByText('Verified')).toBeInTheDocument(); // the toast
  });

  it('transfers the owner and shows why it failed', async () => {
    mockFetch({
      'PATCH /api/v1/folio/nodes/n1/owner': {
        status: 422,
        body: { status: 422, detail: 'Fix these fields: owner', errors: [] },
      },
    });
    renderWithProviders(<PageQuality node={NODE} canManage />);
    await userEvent.click(await screen.findByRole('button', { name: 'Transfer owner' }));
    await userEvent.type(screen.getByLabelText('New owner'), '@nadie');
    await userEvent.click(screen.getAllByRole('button', { name: 'Transfer owner' }).at(-1)!);
    expect(await screen.findByText('Fix these fields: owner')).toBeInTheDocument();
  });

  it('shows nothing to manage for readers', async () => {
    renderWithProviders(<PageQuality node={{ ...NODE, status: 'outdated' }} canManage={false} />);
    expect(await screen.findByText(/past its verification/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Verify' })).toBeNull();
  });
});
