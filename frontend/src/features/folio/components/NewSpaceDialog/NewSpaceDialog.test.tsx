import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { ENGINEERING } from '../TemplatePicker/fixtures';
import { NewSpaceDialog } from '.';
import { keyFor } from './keyFor';

const TEMPLATES = {
  'GET /api/v1/folio/templates': { status: 200, body: { items: [ENGINEERING] } },
};

describe('NewSpaceDialog', () => {
  it('suggests a key from the name', () => {
    expect(keyFor('Ingeniería de Plataforma')).toBe('ingenieria-de-plataforma');
    expect(keyFor('  AI / Tools!  ')).toBe('ai-tools');
  });

  it('creates the space from the template you pick and closes', async () => {
    const calls = mockFetch({
      ...TEMPLATES,
      'POST /api/v1/folio/spaces/from-template': {
        status: 201,
        body: { key: 'ingenieria', name: 'Ingeniería' },
      },
    });
    const onOpenChange = vi.fn();
    renderWithProviders(<NewSpaceDialog open onOpenChange={onOpenChange} />);
    await userEvent.type(await screen.findByLabelText('Name'), 'Ingeniería');
    expect(screen.getByLabelText('Key', { exact: false })).toHaveValue('ingenieria');
    await userEvent.click(await screen.findByRole('radio', { name: /Ingeniería/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    await vi.waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({
      key: 'ingenieria',
      name: 'Ingeniería',
      template: 't2',
    });
  });

  it('creates an empty space and shows why the API refused it', async () => {
    const calls = mockFetch({
      ...TEMPLATES,
      'POST /api/v1/folio/spaces': {
        status: 409,
        body: {
          type: 'about:blank',
          title: 'Conflict',
          status: 409,
          detail: "The space key 'docs' is taken. Choose another.",
          errors: [],
        },
      },
    });
    const onOpenChange = vi.fn();
    renderWithProviders(<NewSpaceDialog open onOpenChange={onOpenChange} />);
    await userEvent.type(await screen.findByLabelText('Name'), 'Docs');
    await userEvent.click(screen.getByRole('button', { name: 'Create' }));
    expect(await screen.findByRole('alert')).toHaveTextContent("The space key 'docs' is taken.");
    expect(calls.find((c) => c.method === 'POST')?.body).toEqual({ key: 'docs', name: 'Docs' });
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });
});
