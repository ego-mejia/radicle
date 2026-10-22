import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SpecsTable } from '.';

const row = (id: string, title: string, extra: Record<string, unknown> = {}) => ({
  node: {
    id,
    kind: 'page',
    title,
    slug: title.toLowerCase().replace(' ', '-'),
    icon: null,
    status: 'published',
  },
  description: `${title}, con sus entregables.`,
  project: 'RAD',
  features: ['Integraciones'],
  status: 'live',
  tickets_done: 1,
  tickets_in_progress: 1,
  tickets_total: 4,
  owner: 'fernando',
  owner_name: 'Fernando Mejía',
  updated_at: '2026-10-22T10:00:00Z',
  ...extra,
});

const LIST = {
  items: [row('11111111-1111-1111-1111-111111111111', 'Fase 5')],
  total: 1,
  projects: [
    { value: 'RAD', count: 6 },
    { value: 'DKT', count: 3 },
  ],
  features: [],
  owners: [{ handle: 'fernando', name: 'Fernando Mejía', count: 4 }],
};

describe('SpecsTable', () => {
  it('lists the specs with their project, feature, progress and status', async () => {
    mockFetch({ 'GET /api/v1/folio/spaces/ing/specs': { status: 200, body: LIST } });
    renderWithProviders(<SpecsTable space="ing" />);
    const link = await screen.findByRole('link', { name: 'Fase 5' });
    expect(link).toHaveAttribute('href', '/folio/p/11111111-1111-1111-1111-111111111111-fase-5');
    const cells = within(link.closest('tr')!);
    expect(cells.getByText('Integraciones')).toBeInTheDocument();
    expect(cells.getByText('In progress')).toBeInTheDocument();
    expect(cells.getByRole('img', { name: '1 of 4 tickets done' })).toBeInTheDocument();
    expect(screen.getByText('1 spec')).toBeInTheDocument();
  });

  it('asks for a project before features, then filters by them', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/spaces/ing/specs': (req) => {
        const project = new URL(req.url).searchParams.get('project');
        const features = project
          ? [
              { value: 'Integraciones', count: 3 },
              { value: 'Móvil', count: 1 },
            ]
          : [];
        return { status: 200, body: { ...LIST, features } };
      },
    });
    renderWithProviders(<SpecsTable space="ing" />);
    await userEvent.click(await screen.findByRole('button', { name: 'Feature: All' }));
    expect(screen.getByText('Pick a project to see its features')).toBeInTheDocument();
    await userEvent.keyboard('{Escape}');
    await userEvent.click(screen.getByRole('button', { name: 'Project: All' }));
    await userEvent.click(screen.getByRole('menuitemradio', { name: /RAD/ }));
    await userEvent.click(await screen.findByRole('button', { name: 'Feature: All' }));
    await userEvent.click(await screen.findByRole('menuitemcheckbox', { name: /Móvil/ }));
    await userEvent.keyboard('{Escape}');
    expect(calls.at(-1)?.path).toContain('project=RAD&feature=M%C3%B3vil');
    await userEvent.click(screen.getByRole('button', { name: 'Remove RAD' }));
    expect(calls.at(-1)?.path).not.toContain('project=');
  });

  it('says when nothing matches and when the list fails', async () => {
    mockFetch({
      'GET /api/v1/folio/spaces/ing/specs': { status: 200, body: { ...LIST, items: [], total: 0 } },
    });
    renderWithProviders(<SpecsTable space="ing" filters={{ features: [], q: 'nada' }} />);
    expect(await screen.findByText('No spec matches these filters.')).toBeInTheDocument();
  });
});
