import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AREA_ICONS, AreaIcon } from '../../../../components/icons/AreaIcon';
import i18n from '../../../../i18n';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { AreaIconPicker } from '.';

describe('AreaIconPicker', () => {
  beforeEach(() => i18n.changeLanguage('en'));

  it('picks an icon from the grid and can clear it', async () => {
    const onPick = vi.fn();
    const view = renderWithProviders(
      <AreaIconPicker area="Infra" icon="server" color="#2563EB" onPick={onPick} />,
    );
    await userEvent.click(await screen.findByRole('button', { name: 'Icon for Infra' }));
    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(Object.keys(AREA_ICONS).length);
    expect(screen.getByRole('option', { name: 'server' })).toHaveAttribute('aria-selected', 'true');
    await userEvent.click(screen.getByRole('option', { name: 'rocket' }));
    expect(onPick).toHaveBeenLastCalledWith('rocket');

    await userEvent.click(screen.getByRole('button', { name: 'Icon for Infra' }));
    await userEvent.click(screen.getByRole('button', { name: 'No icon' }));
    expect(onPick).toHaveBeenLastCalledWith(null);
    view.unmount();
  });
});

describe('AreaIcon', () => {
  it('draws the icon in the area color, or a square without one', () => {
    renderWithProviders(
      <>
        <AreaIcon icon="rocket" color="#2563EB" label="Infra" />
        <AreaIcon icon={null} color="#DB2777" label="Design" />
        <AreaIcon icon="not-in-the-set" label="Old" />
      </>,
    );
    return screen.findByRole('img', { name: 'Infra' }).then((infra) => {
      expect(infra.querySelector('svg')).not.toBeNull();
      expect(infra).toHaveStyle({ color: '#2563EB' });
      expect(screen.getByRole('img', { name: 'Design' }).querySelector('svg')).toBeNull();
      expect(screen.getByRole('img', { name: 'Old' }).querySelector('svg')).toBeNull();
    });
  });
});
