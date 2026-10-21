import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { NodeMenu } from '.';

const NODE = { id: 'n1', title: 'Guía', kind: 'page', space: 'docs' };
const SPACES = {
  items: [
    { key: 'docs', name: 'Docs', permissions: ['view', 'create'] },
    { key: 'ops', name: 'Ops', permissions: ['view', 'create'] },
    { key: 'legal', name: 'Legal', permissions: ['view'] },
  ],
};

async function open(action: RegExp) {
  await userEvent.click(await screen.findByRole('button', { name: 'Actions for Guía' }));
  await userEvent.click(await screen.findByRole('menuitem', { name: action }));
}

describe('NodeMenu', () => {
  it('moves to a space you can write in and shows why it failed', async () => {
    const calls = mockFetch({
      'GET /api/v1/folio/spaces': { status: 200, body: SPACES },
      'GET /api/v1/folio/spaces/docs/tree': { status: 200, body: [] },
      'GET /api/v1/folio/spaces/ops/tree': { status: 200, body: [] },
      'POST /api/v1/folio/nodes/n1/move': {
        status: 403,
        body: { status: 403, detail: "You can't delete 'Guía'", errors: [] },
      },
    });
    renderWithProviders(<NodeMenu node={NODE} />);
    await open(/Move/);
    const space = await screen.findByLabelText('Space');
    expect(await screen.findByRole('option', { name: 'Ops' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Legal' })).toBeNull();
    await userEvent.selectOptions(space, 'ops');
    await userEvent.click(screen.getByRole('button', { name: 'Move' }));
    expect(await screen.findByRole('alert')).toHaveTextContent("You can't delete 'Guía'");
    const move = calls.find((c) => c.path.endsWith('/move'));
    expect(move?.body).toEqual({ space: 'ops', parent: null });
  });

  it('archives after confirming', async () => {
    const calls = mockFetch({
      'POST /api/v1/folio/nodes/n1/archive': { status: 200, body: { id: 'n1', title: 'Guía' } },
    });
    renderWithProviders(<NodeMenu node={NODE} />);
    await open(/Archive/);
    await userEvent.click(await screen.findByRole('button', { name: 'Archive' }));
    expect(await screen.findByText('Archived')).toBeInTheDocument();
    expect(calls.some((c) => c.path.endsWith('/archive'))).toBe(true);
  });

  it('offers only Copy when you may not delete', async () => {
    mockFetch({});
    renderWithProviders(<NodeMenu node={{ ...NODE, can_delete: false }} />);
    await userEvent.click(await screen.findByRole('button', { name: 'Actions for Guía' }));
    expect(await screen.findByRole('menuitem', { name: /Copy/ })).toBeInTheDocument();
    expect(screen.queryByRole('menuitem', { name: /Move/ })).toBeNull();
    expect(screen.queryByRole('menuitem', { name: /Archive/ })).toBeNull();
  });
});
