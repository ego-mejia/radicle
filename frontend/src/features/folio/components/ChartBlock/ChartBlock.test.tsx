import { useState } from 'react';
import { fireEvent, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { DocContent } from '../DocContent';
import { b, doc, p, t } from '../DocContent/testDoc';
import { tableData } from './tableData';

const cell = (type: string, text: string) => b(type, {}, p(t(text)));
const table = (...rows: string[][]) =>
  b(
    'table',
    {},
    ...rows.map((r, i) =>
      b('tableRow', {}, ...r.map((c) => cell(i ? 'tableCell' : 'tableHeader', c))),
    ),
  );

describe('ChartBlock', () => {
  it('reads a document table as chart data', () => {
    const data = tableData(table(['Mes', 'Abiertos'], ['Ene', '1,200'], ['Feb', 'n/a']));
    expect(data).toEqual([
      ['Mes', 'Abiertos'],
      ['Ene', 1200],
      ['Feb', 0],
    ]);
    expect(tableData(table(['Solo'], ['uno']))).toBeNull();
    expect(tableData(p(t('no')))).toBeNull();
  });

  it('switches between the chart and its numbers', async () => {
    const data = [
      ['Mes', 'Abiertos'],
      ['Ene', 4],
    ];
    renderWithProviders(
      <DocContent doc={doc(b('chart', { kind: 'bar', title: 'Tickets', data }))} />,
    );
    expect(await screen.findByRole('img', { name: 'Tickets' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Show table' }));
    const rows = within(screen.getByRole('table')).getAllByRole('row');
    expect(rows[1]).toHaveTextContent('Ene4');
    expect(screen.getByRole('button', { name: 'Show chart' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('draws the table above it and follows its edits', async () => {
    const page = (n: string) =>
      doc(table(['Área', 'Abiertos'], ['Legal', n]), b('chart', { kind: 'line', source: 'table' }));
    function Editing() {
      const [value, setValue] = useState('3');
      return (
        <>
          <button onClick={() => setValue('8')}>edit</button>
          <DocContent doc={page(value)} />
        </>
      );
    }
    renderWithProviders(<Editing />);
    fireEvent.click(await screen.findByRole('button', { name: 'Show table' }));
    const charted = () => screen.getAllByRole('table').at(-1) as HTMLElement;
    expect(charted()).toHaveTextContent('Legal3');
    fireEvent.click(screen.getByRole('button', { name: 'edit' }));
    expect(charted()).toHaveTextContent('Legal8');
  });

  it('asks for data when there is no table before it', async () => {
    renderWithProviders(<DocContent doc={doc(b('chart', { kind: 'bar', source: 'table' }))} />);
    expect(await screen.findByText(/This chart has no data yet/)).toBeInTheDocument();
  });
});
