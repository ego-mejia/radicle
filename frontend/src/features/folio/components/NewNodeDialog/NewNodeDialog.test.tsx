import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
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
});
