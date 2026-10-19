import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import i18n from '../../../../i18n';
import { PROJECT, TICKET } from '../../../../test/fixtures';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { CreateTicketModal } from '.';

const SCHEMA = {
  type: 'task',
  operation: 'create',
  transition: null,
  from_screen: true,
  fields: [
    { field: 'title', label: 'Title', kind: 'text', required: true, options: null, areas: null },
    {
      field: 'area',
      label: 'Area',
      kind: 'area',
      required: true,
      options: ['Backend', 'Legal'],
      areas: null,
    },
    {
      field: 'cf.environment',
      label: 'Environment',
      kind: 'select',
      required: true,
      options: ['prod', 'dev'],
      areas: null,
    },
    {
      field: 'due_date',
      label: 'Due date',
      kind: 'date',
      required: false,
      options: null,
      areas: null,
    },
  ],
};

describe('CreateTicketModal', () => {
  beforeEach(() => i18n.changeLanguage('en'));

  it('builds the form from the screen and checks required fields before sending', async () => {
    const calls = mockFetch({
      'GET /api/v1/projects/PA': { status: 200, body: PROJECT },
      'GET /api/v1/projects/PA/schema': { status: 200, body: SCHEMA },
      'POST /api/v1/projects/PA/tickets': { status: 201, body: TICKET },
    });
    renderWithProviders(
      <CreateTicketModal defaults={{ project: 'PA' }} onClose={() => undefined} />,
    );
    await userEvent.type(await screen.findByRole('textbox', { name: 'Title *' }), 'Login falla');
    const env = await screen.findByRole('combobox', { name: 'Environment *' });
    expect(screen.queryByRole('combobox', { name: /Priority/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    expect(await screen.findAllByText('Required')).toHaveLength(2);
    expect(calls.some((c) => c.method === 'POST')).toBe(false);

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Area *' }), 'Backend');
    await userEvent.selectOptions(env, 'prod');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'POST')).toBe(true));
    const post = calls.find((c) => c.method === 'POST')!;
    expect(post.body).toMatchObject({
      type: 'task',
      title: 'Login falla',
      area: 'Backend',
      priority: 'medium',
      custom_fields: { environment: 'prod' },
    });
  });
});
