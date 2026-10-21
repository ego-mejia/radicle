import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRef } from 'react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { DocContent } from '../DocContent';
import { b, doc, t } from '../DocContent/testDoc';
import { ActionItemTickets } from '.';

const NODE = '11111111-1111-1111-1111-111111111111';
const PROJECT = { key: 'PA', name: 'ProyectoA', areas: [], milestones: [] };
const DOC = doc(
  b('heading', { level: 2 }, t('Siguientes pasos')),
  b('actionItem', { id: 'ai-1', assignee: 'luis' }, t('Publicar la guía')),
);

function Page() {
  const ref = useRef<HTMLDivElement>(null);
  return (
    <div ref={ref}>
      <ActionItemTickets nodeId={NODE} container={ref}>
        <DocContent doc={DOC} />
      </ActionItemTickets>
    </div>
  );
}

describe('ActionItemTickets', () => {
  it('makes an action item a ticket linked to its section', async () => {
    const calls = mockFetch({
      'GET /api/v1/projects': { status: 200, body: { items: [PROJECT] } },
      'GET /api/v1/projects/PA': { status: 200, body: PROJECT },
      [`POST /api/v1/folio/nodes/${NODE}/tickets`]: {
        status: 201,
        body: { id: 'l1', kind: 'created_from_text', ticket: { key: 'PA-8' }, restricted: false },
      },
    });
    renderWithProviders(<Page />);
    await userEvent.click(
      await screen.findByRole('button', { name: 'Create a ticket from this action item' }),
    );
    expect(await screen.findByRole('dialog', { name: 'Create ticket' })).toHaveTextContent(
      '“Publicar la guía”',
    );
    await screen.findByRole('option', { name: 'PA · ProyectoA' });
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    expect(await screen.findByText('PA-8 created and linked to this section.')).toBeVisible();
    const post = calls.find((c) => c.method === 'POST');
    expect(post?.body).toMatchObject({ text: 'Publicar la guía', anchor: 'siguientes-pasos' });
  });

  it('offers nothing outside a page that allows it', async () => {
    renderWithProviders(<DocContent doc={DOC} />);
    await screen.findByText('Publicar la guía');
    expect(screen.queryByRole('button', { name: /Create a ticket/ })).toBeNull();
  });
});
