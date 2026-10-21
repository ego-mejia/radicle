import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../../../test/renderWithProviders';
import type { Metadata } from '../../validate';
import { MetadataForm } from '.';

const entry = (key: string, name: string) => ({
  key,
  name,
  description: '',
  position: 0,
  active: true,
});
const SCHEMA = {
  fields: [],
  doc_types: [entry('how-to', 'How-to')],
  audiences: [entry('everyone', 'Everyone'), entry('eng', 'Engineering')],
  languages: [entry('es', 'Español')],
};
const EMPTY: Metadata = {
  description: '',
  doc_type: '',
  labels: [],
  owner: 'luis',
  audiences: [],
  language: '',
};

function Harness({ onChange }: { onChange: (m: Metadata) => void }) {
  const [value, setValue] = useState(EMPTY);
  const [labels, setLabels] = useState('');
  return (
    <MetadataForm
      value={value}
      labelsText={labels}
      onChange={(m) => (setValue(m), onChange(m))}
      onLabelsText={setLabels}
      onBlur={() => undefined}
      schema={SCHEMA as never}
      errors={{ language: 'Choose a language.' }}
    />
  );
}

describe('MetadataForm', () => {
  it('edits every field from the catalogs and shows errors on them', async () => {
    const onChange = vi.fn();
    renderWithProviders(<Harness onChange={onChange} />);
    await userEvent.selectOptions(await screen.findByLabelText('Document type'), 'how-to');
    await userEvent.type(screen.getByLabelText('Labels'), '#Onboarding, mcp');
    await userEvent.click(screen.getByRole('checkbox', { name: 'Engineering' }));
    await userEvent.clear(screen.getByLabelText('Owner'));
    await userEvent.type(screen.getByLabelText('Owner'), '@ana');
    expect(onChange.mock.lastCall?.[0]).toEqual({
      ...EMPTY,
      doc_type: 'how-to',
      labels: ['onboarding', 'mcp'],
      audiences: ['eng'],
      owner: 'ana',
    });
    expect(screen.getByText('Choose a language.')).toBeInTheDocument();
    expect(screen.getByText('0/400')).toBeInTheDocument();
  });
});
