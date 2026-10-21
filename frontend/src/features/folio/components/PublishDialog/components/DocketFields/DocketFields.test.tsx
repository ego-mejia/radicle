import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../../../test/renderWithProviders';
import { fromDraft, type Metadata } from '../../validate';
import { DocketFields } from '.';

const PROJECT = {
  key: 'PA',
  name: 'ProyectoA',
  archived: false,
  areas: [
    { name: 'Backend', archived: false },
    { name: 'Viejo', archived: true },
  ],
  milestones: [
    { name: 'V1', status: 'open' },
    { name: 'V0', status: 'closed' },
  ],
};

let latest: Metadata;
function Form({ initial }: { initial: Record<string, unknown> }) {
  const [value, setValue] = useState(() => fromDraft(initial, 'luis'));
  latest = value;
  return (
    <DocketFields
      value={value}
      onChange={setValue}
      errors={{ docket_areas: 'set docket_project too' }}
    />
  );
}

describe('DocketFields', () => {
  it('links the doc to a project, its open milestones and areas', async () => {
    mockFetch({
      'GET /api/v1/projects': { status: 200, body: { items: [PROJECT] } },
      'GET /api/v1/projects/PA': { status: 200, body: PROJECT },
    });
    renderWithProviders(<Form initial={{}} />);
    expect(await screen.findByText('Optional')).toBeVisible();
    await userEvent.click(screen.getByText('Docket'));
    await screen.findByRole('option', { name: 'PA · ProyectoA' });
    await userEvent.selectOptions(screen.getByLabelText(/^Project/), 'PA');
    await userEvent.click(await screen.findByRole('checkbox', { name: 'V1' }));
    await userEvent.click(screen.getByRole('checkbox', { name: 'Backend' }));
    expect(screen.queryByRole('checkbox', { name: 'V0' })).toBeNull();
    expect(screen.queryByRole('checkbox', { name: 'Viejo' })).toBeNull();
    expect(screen.getByText('PA · 2 links')).toBeVisible();
    expect(screen.getByText('set docket_project too')).toBeVisible();
    expect(latest).toMatchObject({
      docket_project: 'PA',
      docket_milestones: ['V1'],
      docket_areas: ['Backend'],
    });
    await userEvent.selectOptions(screen.getByLabelText(/^Project/), '');
    expect(latest).toMatchObject({ docket_project: '', docket_milestones: [], docket_areas: [] });
  });

  it('keeps a closed milestone the doc already names', async () => {
    mockFetch({
      'GET /api/v1/projects': { status: 200, body: { items: [PROJECT] } },
      'GET /api/v1/projects/PA': { status: 200, body: PROJECT },
    });
    renderWithProviders(<Form initial={{ docket_project: 'pa', docket_milestones: ['V0'] }} />);
    expect(await screen.findByRole('checkbox', { name: 'V0' })).toBeChecked();
  });
});
