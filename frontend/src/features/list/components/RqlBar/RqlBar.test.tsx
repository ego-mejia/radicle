import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../../../i18n';
import type { SearchFields } from '../../../../services/api/types';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { RqlBar } from '.';

const FIELDS: SearchFields = {
  fields: [
    {
      name: 'priority',
      type: 'ordinal',
      operators: ['=', '!=', '>='],
      supports_in: true,
      supports_empty: false,
      description: '',
      values: ['highest', 'high'],
    },
    {
      name: 'project',
      type: 'project',
      operators: ['=', '!='],
      supports_in: true,
      supports_empty: false,
      description: '',
      values: [],
    },
    {
      name: 'area',
      type: 'name',
      operators: ['=', '!='],
      supports_in: true,
      supports_empty: true,
      description: '',
      values: [],
    },
  ],
  sort_fields: ['priority', 'updated'],
  functions: ['currentUser()'],
  keywords: ['AND'],
  values: {
    project: 'PA',
    statuses: [],
    areas: ['Legal', 'Backend'],
    milestones: [],
    handles: [],
    tags: [],
  },
};

describe('RqlBar', () => {
  beforeEach(() => i18n.changeLanguage('en'));

  it('shows the error and underlines the token at its position', async () => {
    renderWithProviders(
      <RqlBar
        value="type = bug AND prioridad = high"
        fields={FIELDS}
        onSubmit={() => undefined}
        error={{ message: "Unknown field 'prioridad' at 15.", position: 15 }}
      />,
    );
    expect(await screen.findByRole('alert')).toHaveTextContent("Unknown field 'prioridad' at 15.");
    expect(screen.getByRole('textbox')).toHaveAttribute('aria-invalid', 'true');
    expect(document.querySelector('mark')).toHaveTextContent('prioridad');
  });

  it('suggests fields, operators and values and submits', async () => {
    const onSubmit = vi.fn();
    renderWithProviders(<RqlBar value="" fields={FIELDS} onSubmit={onSubmit} />);
    const input = await screen.findByRole('textbox');
    await userEvent.type(input, 'ar');
    expect(screen.getByRole('option', { name: /area/ })).toBeInTheDocument();
    await userEvent.keyboard('{Tab}');
    expect(input).toHaveValue('area ');
    expect(screen.getByRole('option', { name: '=' })).toBeInTheDocument();
    await userEvent.keyboard('{Tab}');
    expect(screen.getByRole('option', { name: 'Legal' })).toBeInTheDocument();
    await userEvent.keyboard('{ArrowDown}{Tab}');
    expect(input).toHaveValue('area = Backend ');
    await userEvent.keyboard('{Enter}');
    expect(onSubmit).toHaveBeenCalledWith('area = Backend');
  });
});
