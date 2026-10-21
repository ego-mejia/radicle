import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SPEC } from '../TemplatePicker/fixtures';
import { NewNodeDialog } from '.';

describe('NewNodeDialog', () => {
  it('shows what the API says is wrong and keeps the dialog open', async () => {
    const calls = mockFetch({
      'POST /api/v1/folio/nodes': {
        status: 403,
        body: {
          type: 'about:blank',
          title: 'Forbidden',
          status: 403,
          detail: 'You cannot write here.',
          errors: [],
        },
      },
    });
    const onOpenChange = vi.fn();
    renderWithProviders(
      <NewNodeDialog space="docs" kind="blog_post" parent="p1" open onOpenChange={onOpenChange} />,
    );
    expect(await screen.findByRole('dialog', { name: 'New blog post' })).toBeInTheDocument();
    const create = screen.getByRole('button', { name: 'Create' });
    expect(create).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Title'), 'Novedades');
    await userEvent.click(create);
    expect(await screen.findByText('You cannot write here.')).toBeInTheDocument();
    // Blog posts never have a parent.
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      space: 'docs',
      kind: 'blog_post',
      title: 'Novedades',
      parent: null,
    });
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });

  it('creates a page from the template you pick', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/templates': { status: 200, body: { items: [SPEC] } },
      'POST /api/v1/folio/nodes/from-template': {
        status: 201,
        body: { id: 'n9', slug: 'etapa-5', space: 'docs' },
      },
    });
    renderWithProviders(<NewNodeDialog space="docs" kind="page" open onOpenChange={vi.fn()} />);
    await userEvent.type(await screen.findByLabelText('Title'), 'Etapa 5');
    await userEvent.click(await screen.findByRole('radio', { name: /Build spec/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    await vi.waitFor(() =>
      expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
        space: 'docs',
        title: 'Etapa 5',
        parent: null,
        template: 't1',
        kind: 'page',
      }),
    );
  });

  it('folders have no templates', async () => {
    mockFetch({});
    renderWithProviders(<NewNodeDialog space="docs" kind="folder" open onOpenChange={vi.fn()} />);
    expect(await screen.findByRole('dialog', { name: 'New folder' })).toBeInTheDocument();
    expect(screen.queryByRole('radiogroup')).toBeNull();
  });
});
