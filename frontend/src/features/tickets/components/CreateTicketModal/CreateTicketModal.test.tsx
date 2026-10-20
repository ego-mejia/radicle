import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../../../i18n';
import { PROJECT, TICKET } from '../../../../test/fixtures';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { CreateTicketModal } from '.';

const upload = vi.fn();
vi.mock('../../../../services/api/attachments', async (original) => ({
  ...(await original<typeof import('../../../../services/api/attachments')>()),
  uploadAttachment: (...args: unknown[]) => upload(...args),
}));

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

describe('pasting a file before the ticket exists', () => {
  beforeEach(() => {
    i18n.changeLanguage('en');
    URL.createObjectURL = () => 'blob:shot';
    URL.revokeObjectURL = () => undefined;
    upload.mockReset().mockResolvedValue({ markdown: '![shot.png](/a/1)' });
  });

  it('shows it, then uploads it and puts its markdown in the description', async () => {
    const field = (name: string) => ({
      field: name,
      label: name,
      kind: 'text',
      required: name === 'title',
      options: null,
      areas: null,
    });
    const calls = mockFetch({
      'GET /api/v1/projects/PA': { status: 200, body: PROJECT },
      'GET /api/v1/projects/PA/schema': {
        status: 200,
        body: { ...SCHEMA, fields: [field('title'), field('description_md')] },
      },
      'POST /api/v1/projects/PA/tickets': (_, body) => ({
        status: 201,
        body: { ...TICKET, description_md: (body as { description_md: string }).description_md },
      }),
      'GET /api/v1/tickets/PA-4': { status: 200, body: { ...TICKET, version: 5 } },
      'PATCH /api/v1/tickets/PA-4': { status: 200, body: TICKET },
    });
    renderWithProviders(
      <CreateTicketModal defaults={{ project: 'PA' }} onClose={() => undefined} />,
    );
    await userEvent.type(await screen.findByRole('textbox', { name: 'Title *' }), 'Broken');
    const file = new File(['png'], 'shot.png', { type: 'image/png' });
    const editor = await screen.findByRole('textbox', { name: 'Description' });
    fireEvent.paste(editor, { clipboardData: { files: [file], items: [] } });
    expect(await screen.findByRole('img', { name: 'shot.png' })).toBeInTheDocument();
    expect(screen.getByText('Uploads when the ticket is created')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    await waitFor(() => expect(calls.some((c) => c.method === 'PATCH')).toBe(true));
    expect(upload).toHaveBeenCalledWith('PA-4', file);
    expect(calls.find((c) => c.method === 'PATCH')!.body).toEqual({
      description_md: '![shot.png](/a/1)',
      expected_version: 5,
    });
  });
});
