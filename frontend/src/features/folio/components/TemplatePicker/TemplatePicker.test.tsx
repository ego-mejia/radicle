import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { SPEC } from './fixtures';
import { TemplatePicker } from '.';

function Harness() {
  const [value, setValue] = useState<string | null>(null);
  return <TemplatePicker space="docs" value={value} onChange={setValue} />;
}

describe('TemplatePicker', () => {
  it('starts blank and previews the template you pick', async () => {
    mockFetch({ 'GET /api/v1/folio/templates': { status: 200, body: { items: [SPEC] } } });
    renderWithProviders(<Harness />);
    const blank = await screen.findByRole('radio', { name: /Blank page/ });
    expect(blank).toHaveAttribute('aria-checked', 'true');
    await userEvent.click(await screen.findByRole('radio', { name: /Build spec/ }));
    expect(screen.getByRole('radio', { name: /Build spec/ })).toHaveAttribute(
      'aria-checked',
      'true',
    );
    const preview = screen.getByRole('region', { name: 'Preview of Build spec' });
    expect(preview).toHaveTextContent('Entregables');
  });
});
