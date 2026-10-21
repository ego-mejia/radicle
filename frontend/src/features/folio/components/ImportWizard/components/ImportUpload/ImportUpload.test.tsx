import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../../../test/renderWithProviders';
import { ImportUpload } from '.';

const spaces = [
  { key: 'eng', name: 'Ingeniería', kind: 'team', permissions: ['view', 'admin'] },
  { key: 'ops', name: 'Operaciones', kind: 'team', permissions: ['view'] },
  { key: '~ana', name: 'Ana', kind: 'personal', permissions: ['view', 'admin'] },
];

describe('ImportUpload', () => {
  it('uploads into a space you administer', async () => {
    const made = { id: 'i1', status: 'uploaded' };
    const calls = mockFetch({
      'GET /api/v1/folio/spaces': { status: 200, body: { items: spaces } },
      'POST /api/v1/folio/imports': { status: 201, body: made },
    });
    const onUploaded = vi.fn();
    renderWithProviders(<ImportUpload onUploaded={onUploaded} />);
    await waitFor(() =>
      expect(screen.getByRole('option', { name: 'Ingeniería' })).toBeInTheDocument(),
    );
    expect(screen.queryByRole('option', { name: 'Operaciones' })).not.toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Ana' })).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText('From'), 'notion');
    expect(screen.getByText(/Markdown & CSV\./)).toBeInTheDocument();
    const button = screen.getByRole('button', { name: 'Upload and check' });
    expect(button).toBeDisabled();
    await userEvent.upload(screen.getByLabelText('Export file'), new File(['z'], 'n.zip'));
    await userEvent.click(button);
    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith(made));
    expect(calls.some((c) => c.method === 'POST' && c.path === '/api/v1/folio/imports')).toBe(true);
  });

  it('says why an upload is refused, and when there is no space to import into', async () => {
    mockFetch({
      'GET /api/v1/folio/spaces': { status: 200, body: { items: [spaces[0]] } },
      'POST /api/v1/folio/imports': {
        status: 422,
        body: { status: 422, detail: 'The zip has no files to import.', errors: [] },
      },
    });
    renderWithProviders(<ImportUpload onUploaded={vi.fn()} />);
    await waitFor(() =>
      expect(screen.getByRole('option', { name: 'Ingeniería' })).toBeInTheDocument(),
    );
    await userEvent.upload(screen.getByLabelText('Export file'), new File(['x'], 'a.zip'));
    await userEvent.click(screen.getByRole('button', { name: 'Upload and check' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('The zip has no files to import.');
  });

  it('explains that only space admins import', async () => {
    mockFetch({ 'GET /api/v1/folio/spaces': { status: 200, body: { items: [spaces[1]] } } });
    renderWithProviders(<ImportUpload onUploaded={vi.fn()} />);
    expect(await screen.findByText(/only a space's admins import into it/)).toBeInTheDocument();
  });
});
