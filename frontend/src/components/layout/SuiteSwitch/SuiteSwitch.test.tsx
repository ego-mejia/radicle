import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ME, makeClient, renderWithProviders } from '../../../test/renderWithProviders';
import { folioKeys } from '../../../services/api/folio';
import { SuiteSwitch } from '.';

const reader = { handle: 'luis', display_name: 'Luis', kind: 'human', role: 'reader' };

function setup(folio: typeof reader | null, admin = false) {
  const client = makeClient({ ...ME, is_instance_admin: admin });
  client.setQueryData(folioKeys.me, folio);
  renderWithProviders(<SuiteSwitch current="docket" />, client);
}

describe('SuiteSwitch', () => {
  it('lists both apps, marks the current one and shows the shortcut of the other', async () => {
    setup(reader);
    const trigger = await screen.findByRole('button', { name: /Switch app, now Radicle Docket/ });
    expect(trigger).toHaveTextContent('DOCKET');
    await userEvent.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
    const docket = await screen.findByRole('menuitem', { name: /Radicle Docket/ });
    expect(docket).toHaveAttribute('aria-current', 'true');
    expect(screen.getByRole('menuitem', { name: /Radicle Folio/ })).toHaveTextContent('G F');
    expect(screen.queryByRole('menuitem', { name: /Instance administration/ })).toBeNull();
    await userEvent.keyboard('{Escape}');
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
  });

  it('hides Folio when no grant reaches the user, and offers admin to instance admins', async () => {
    setup(null, true);
    await userEvent.click(await screen.findByRole('button', { name: /Switch app/ }));
    expect(await screen.findByRole('menuitem', { name: /Radicle Docket/ })).toBeInTheDocument();
    expect(screen.queryByRole('menuitem', { name: /Radicle Folio/ })).toBeNull();
    expect(screen.getByRole('menuitem', { name: /Instance administration/ })).toBeInTheDocument();
  });
});
