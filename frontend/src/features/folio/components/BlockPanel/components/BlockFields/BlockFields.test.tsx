import { fireEvent, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { renderWithProviders } from '../../../../../../test/renderWithProviders';
import { BlockFields } from '.';
import { chartToText, textToChart, textToTimeline, timelineToText } from './text';

describe('BlockFields', () => {
  it('writes charts and timelines as text and reads them back', () => {
    const data = [
      ['Mes', 'Abiertos'],
      ['Ene', 1200],
    ];
    expect(textToChart(chartToText(data))).toEqual(data);
    expect(textToChart('a | b\nx | 1,5 | extra\ny')).toEqual([
      ['a', 'b'],
      ['x', 15], // thousands commas, as the server reads them
      ['y', 0],
    ]);
    const items = [
      { date: 'Q1', title: 'Beta', status: 'done' as const },
      { title: 'GA', text: 'con | barra', status: 'in_progress' as const },
      { title: 'Sin fecha' },
    ];
    expect(timelineToText(items)).toBe('[x] Q1 | Beta\n[~]  | GA | con | barra\n | Sin fecha');
    expect(textToTimeline(timelineToText(items))).toEqual(items);
    expect(textToTimeline('[ ] 2027 | 2.0\n | ')).toEqual([
      { date: '2027', title: '2.0', status: 'planned' },
    ]);
  });

  it('edits a chart: kind, its own numbers or the table before it', async () => {
    const onChange = vi.fn();
    const attrs = {
      kind: 'bar',
      data: [
        ['M', 'N'],
        ['a', 1],
      ],
    };
    renderWithProviders(<BlockFields type="chart" attrs={attrs} onChange={onChange} />);
    fireEvent.change(await screen.findByLabelText('Numbers'), {
      target: { value: 'M | N\na | 7' },
    });
    expect(onChange).toHaveBeenLastCalledWith({
      data: [
        ['M', 'N'],
        ['a', 7],
      ],
    });
    fireEvent.change(screen.getByLabelText('Kind'), { target: { value: 'pie' } });
    expect(onChange).toHaveBeenLastCalledWith({ kind: 'pie' });
    fireEvent.change(screen.getByLabelText('Data'), { target: { value: 'table' } });
    expect(onChange).toHaveBeenLastCalledWith({ source: 'table', data: null });
  });

  it('edits a page list with a clean label and a limit within 1 to 50', async () => {
    const onChange = vi.fn();
    renderWithProviders(<BlockFields type="pageList" attrs={{ label: '' }} onChange={onChange} />);
    fireEvent.change(await screen.findByLabelText('Label'), { target: { value: '#Onboarding' } });
    expect(onChange).toHaveBeenLastCalledWith({ label: 'onboarding' });
    fireEvent.change(screen.getByLabelText('How many'), { target: { value: '99' } });
    expect(onChange).toHaveBeenLastCalledWith({ limit: 50 });
    fireEvent.change(screen.getByLabelText('Order'), { target: { value: 'title' } });
    expect(onChange).toHaveBeenLastCalledWith({ order: 'title' });
  });

  it('edits a diagram and a formula', async () => {
    const onChange = vi.fn();
    renderWithProviders(
      <>
        <BlockFields type="diagram" attrs={{ source: 'graph TD' }} onChange={onChange} />
        <BlockFields type="formula" attrs={{ latex: 'x' }} onChange={onChange} />
      </>,
    );
    fireEvent.change(await screen.findByLabelText('Mermaid source'), {
      target: { value: 'graph LR' },
    });
    expect(onChange).toHaveBeenLastCalledWith({ source: 'graph LR' });
    fireEvent.change(screen.getByLabelText('LaTeX'), { target: { value: 'y^2' } });
    expect(onChange).toHaveBeenLastCalledWith({ latex: 'y^2' });
  });
});
