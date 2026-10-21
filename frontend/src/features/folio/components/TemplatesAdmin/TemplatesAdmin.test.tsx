import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SPEC } from '../TemplatePicker/fixtures';
import { TemplatesAdmin } from '.';

describe('TemplatesAdmin', () => {
  it('lists page and space templates and archives one after confirming', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/templates': (req) => ({
        status: 200,
        body: {
          items: new URL(req.url).searchParams.get('kind') === 'page' ? [SPEC] : [],
        },
      }),
      'DELETE /api/v1/folio/templates/t1': { status: 204, body: null },
    });
    renderWithProviders(<TemplatesAdmin />);
    const pages = (await screen.findByRole('heading', { name: 'Page templates' })).closest(
      'section',
    ) as HTMLElement;
    expect(await within(pages).findByRole('link', { name: 'Build spec' })).toBeInTheDocument();
    expect(within(pages).getByText('Included')).toBeInTheDocument();
    expect(await screen.findByText('No templates yet.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Archive Build spec' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Archive' }));
    await vi.waitFor(() =>
      expect(calls.some((c) => c.method === 'DELETE' && c.path.endsWith('/t1'))).toBe(true),
    );
  });
});
