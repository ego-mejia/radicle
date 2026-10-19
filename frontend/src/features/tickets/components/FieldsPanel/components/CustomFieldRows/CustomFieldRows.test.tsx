import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../../../../../i18n';
import { PROJECT, TICKET } from '../../../../../../test/fixtures';
import { renderWithProviders } from '../../../../../../test/renderWithProviders';
import { appliesTo } from '../../../../../../lib/customFields';
import { CustomFieldRows } from '.';

describe('CustomFieldRows', () => {
  beforeEach(() => i18n.changeLanguage('en'));

  it('shows only fields that apply and marks a removed option', async () => {
    const onChange = vi.fn();
    renderWithProviders(
      <CustomFieldRows
        ticket={TICKET}
        fields={PROJECT.custom_fields}
        people={PROJECT.members}
        canEdit
        onChange={onChange}
      />,
    );
    const select = await screen.findByRole('combobox', { name: 'Environment' });
    expect(select).toHaveDisplayValue('staging (removed option)');
    expect(screen.queryByText('Contract')).not.toBeInTheDocument();

    await userEvent.selectOptions(select, 'prod');
    expect(onChange).toHaveBeenCalledWith('environment', 'prod');
  });

  it('matches by type and area', () => {
    const contract = PROJECT.custom_fields[1]!;
    expect(appliesTo(contract, { type: 'task', area: 'Legal' })).toBe(true);
    expect(appliesTo(contract, { type: 'task', area: 'Backend' })).toBe(false);
    expect(appliesTo(contract, { type: 'bug', area: 'Legal' })).toBe(false);
  });
});
