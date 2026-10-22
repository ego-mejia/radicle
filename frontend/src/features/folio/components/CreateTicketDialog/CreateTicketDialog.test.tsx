import { fireEvent, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRef } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { rangeOf } from '../../hooks/textAnchor';
import { SelectionComment } from '../SelectionComment';

const NODE = '11111111-1111-1111-1111-111111111111';
const PROJECT = {
  key: 'PA',
  name: 'ProyectoA',
  archived: false,
  areas: [{ name: 'Backend', archived: false }],
  milestones: [
    { name: 'V1', status: 'open' },
    { name: 'V0', status: 'closed' },
  ],
};

function Page() {
  const ref = useRef<HTMLDivElement>(null);
  return (
    <>
      <div ref={ref} data-testid="page">
        <h2 id="conecta-un-agente">Conecta un agente</h2>
        <p>Documentar el token del agente.</p>
      </div>
      <SelectionComment container={ref} mentions={[]} ticketNode={{ id: NODE }} />
    </>
  );
}

function select(page: HTMLElement, quote: string) {
  const selection = window.getSelection()!;
  selection.removeAllRanges();
  selection.addRange(rangeOf(page, quote)!);
  fireEvent.mouseUp(page);
}

describe('CreateTicketDialog', () => {
  it('creates a ticket from the selection, linked to its section', async () => {
    const calls = mockFetch({
      'GET /api/v1/projects': { status: 200, body: { items: [PROJECT] } },
      'GET /api/v1/projects/PA': { status: 200, body: PROJECT },
      [`POST /api/v1/folio/nodes/${NODE}/tickets`]: {
        status: 201,
        body: { id: 'l1', kind: 'created_from_text', ticket: { key: 'PA-7' }, restricted: false },
      },
    });
    renderWithProviders(<Page />);
    select(await screen.findByTestId('page'), 'Documentar el token');
    // Without the comment permission only "Create ticket" is offered.
    expect(screen.queryByRole('button', { name: 'Comment on the selected text' })).toBeNull();
    await userEvent.click(await screen.findByRole('button', { name: 'Create ticket' }));
    const dialog = await screen.findByRole('dialog', { name: 'Create ticket' });
    expect(dialog).toHaveTextContent('“Documentar el token”');
    await screen.findByRole('option', { name: 'Backend' });
    expect(screen.queryByRole('option', { name: 'V0' })).toBeNull();
    await userEvent.selectOptions(screen.getByLabelText(/^Area/), 'Backend');
    await userEvent.selectOptions(screen.getByLabelText('Milestone'), 'V1');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    expect(await screen.findByText('PA-7 created and linked to this section.')).toBeVisible();
    const post = calls.find((c) => c.method === 'POST');
    expect(post?.body).toEqual({
      text: 'Documentar el token',
      anchor: 'conecta-un-agente',
      project: 'PA',
      title: 'Documentar el token',
      type: 'task',
      area: 'Backend',
      milestone: 'V1',
    });
  });

  it("starts on the doc's own Docket project", async () => {
    const other = { ...PROJECT, key: 'PB', name: 'ProyectoB' };
    const calls = mockFetch({
      'GET /api/v1/projects': { status: 200, body: { items: [PROJECT, other] } },
      'GET /api/v1/projects/PA': { status: 200, body: PROJECT },
      'GET /api/v1/projects/PB': { status: 200, body: other },
      [`GET /api/v1/folio/nodes/${NODE}`]: {
        status: 200,
        body: { id: NODE, metadata: { docket_project: 'pb' } },
      },
      [`POST /api/v1/folio/nodes/${NODE}/tickets`]: {
        status: 201,
        body: { id: 'l1', kind: 'created_from_text', ticket: { key: 'PB-2' }, restricted: false },
      },
    });
    renderWithProviders(<Page />);
    select(await screen.findByTestId('page'), 'Documentar el token');
    await userEvent.click(await screen.findByRole('button', { name: 'Create ticket' }));
    await screen.findByRole('dialog', { name: 'Create ticket' });
    await vi.waitFor(() => expect(screen.getByLabelText('Project')).toHaveValue('PB'));
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    expect(await screen.findByText('PB-2 created and linked to this section.')).toBeVisible();
    expect(calls.find((c) => c.method === 'POST')?.body).toMatchObject({ project: 'PB' });
  });

  it("shows Docket's reason when it refuses", async () => {
    mockFetch({
      'GET /api/v1/projects': { status: 200, body: { items: [PROJECT] } },
      'GET /api/v1/projects/PA': { status: 200, body: PROJECT },
      [`POST /api/v1/folio/nodes/${NODE}/tickets`]: {
        status: 422,
        body: { status: 422, detail: 'Tasks need an area. Areas: Backend.', errors: [] },
      },
    });
    renderWithProviders(<Page />);
    select(await screen.findByTestId('page'), 'Documentar');
    await userEvent.click(await screen.findByRole('button', { name: 'Create ticket' }));
    await screen.findByRole('option', { name: 'PA · ProyectoA' });
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Tasks need an area');
  });
});
