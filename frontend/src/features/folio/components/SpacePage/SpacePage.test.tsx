import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SpacePage } from '.';

const SPACE = {
  key: 'docs',
  name: 'Ingeniería',
  description: 'Cómo construimos Radicle.',
  kind: 'team',
  icon: null,
  cover_asset_id: null,
  created_at: '2026-10-20T10:00:00Z',
  permissions: ['view', 'create'],
};
const TREE = [
  { id: 'p1', kind: 'page', title: 'Deploy', slug: 'deploy', icon: null, children: [] },
];
const POSTS = [
  {
    id: 'b1',
    kind: 'blog_post',
    title: 'Novedades',
    slug: 'novedades',
    icon: null,
    status: 'published',
  },
];

function api(space: object = SPACE) {
  return mockFetch({
    'GET /api/v1/folio/spaces/docs': { status: 200, body: space },
    'GET /api/v1/folio/spaces/docs/tree': { status: 200, body: TREE },
    'GET /api/v1/folio/spaces/docs/posts': { status: 200, body: { items: POSTS } },
    'POST /api/v1/folio/nodes': (_r, body) => ({
      status: 201,
      body: { id: 'f9', slug: 'nueva', ...(body as object) },
    }),
  });
}

describe('SpacePage', () => {
  it('shows the space, its tree and its posts', async () => {
    api();
    renderWithProviders(<SpacePage spaceKey="docs" />);
    expect(await screen.findByRole('heading', { name: 'Ingeniería' })).toBeInTheDocument();
    expect(screen.getByText('Cómo construimos Radicle.')).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'Deploy' })).toHaveAttribute(
      'href',
      '/folio/p/p1-deploy',
    );
    expect(await screen.findByRole('link', { name: 'Novedades' })).toHaveAttribute(
      'href',
      '/folio/p/b1-novedades',
    );
    expect(screen.getByRole('button', { name: 'Move Deploy' })).toBeInTheDocument();
  });

  it('creates a folder in the space', async () => {
    const calls = api();
    renderWithProviders(<SpacePage spaceKey="docs" />);
    await userEvent.click(await screen.findByRole('button', { name: 'New folder' }));
    await userEvent.type(screen.getByLabelText('Title'), 'Guías');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    await waitFor(() =>
      expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
        space: 'docs',
        kind: 'folder',
        title: 'Guías',
        parent: null,
      }),
    );
  });

  it('hides writing to readers', async () => {
    api({ ...SPACE, permissions: ['view'] });
    renderWithProviders(<SpacePage spaceKey="docs" />);
    expect(await screen.findByRole('heading', { name: 'Ingeniería' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'New page' })).toBeNull();
    expect(await screen.findByRole('link', { name: 'Deploy' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Move Deploy' })).toBeNull();
  });

  it('explains a space it cannot open', async () => {
    mockFetch({});
    renderWithProviders(<SpacePage spaceKey="docs" />);
    expect(await screen.findByText('This space is not available')).toBeInTheDocument();
  });
});
