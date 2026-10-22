import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { GuidesSection } from '.';

const guide = (id: string, title: string, labels: string[]) => ({
  id,
  slug: id,
  title,
  kind: 'page',
  icon: null,
  space: 'eng',
  parent_id: null,
  version: 1,
  metadata: { description: `Sobre ${title}`, labels },
  published_at: '2026-10-20T12:00:00Z',
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-20T12:00:00Z',
});

const PATH = [
  guide('g1', '1. Onboarding', ['getting-started']),
  guide('g2', '2. Levanta Radicle', ['getting-started']),
  guide('g3', '3. Tu primer PR', ['getting-started']),
];
const ALL = [
  ...PATH,
  guide('g4', 'Guía de despliegue', ['#despliegue']),
  guide('g5', 'Conectar un agente', ['agentes']),
];

describe('GuidesSection', () => {
  it('marks the path by what you read and filters guides by category', async () => {
    mockFetch({
      'GET /api/v1/folio/nodes': (req) => {
        const q = new URL(req.url).searchParams.get('q') ?? '';
        return { status: 200, body: { items: q.includes('getting-started') ? PATH : ALL } };
      },
      'GET /api/v1/folio/me/recents': {
        status: 200,
        body: {
          items: [
            {
              id: 'g1',
              kind: 'page',
              title: '1. Onboarding',
              slug: 'g1',
              icon: null,
              status: 'published',
            },
          ],
        },
      },
    });
    renderWithProviders(<GuidesSection space="eng" />);
    expect(await screen.findByText('Read')).toBeInTheDocument();
    expect(screen.getByText('Up next')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'despliegue' }));
    expect(screen.getByRole('link', { name: /Guía de despliegue/ })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Conectar un agente/ })).not.toBeInTheDocument();
  });
});
