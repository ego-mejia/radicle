import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { DbColumn } from '../../../../services/api/folioDatabases';
import { columnKey } from '../../../../services/api/folioDatabases';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { COLUMNS } from '../DatabaseView/fixtures';
import { DbValue } from '.';

const col = (type: DbColumn['type']): DbColumn => ({ key: 'x', name: 'X', type, options: {} });

describe('DbValue', () => {
  it('shows each type its own way', async () => {
    renderWithProviders(
      <>
        <DbValue column={COLUMNS[1]!} value="Adopted" />
        <DbValue column={col('person')} value="vera" />
        <DbValue column={col('url')} value="https://claude.ai/code" />
        <DbValue column={col('checkbox')} value={true} />
        <DbValue column={col('checkbox')} value={false} />
        <DbValue column={col('page')} value="p1" />
        <DbValue column={col('multi_select')} value={['ai', 'llm']} />
        <DbValue column={col('text')} value={null} />
      </>,
    );
    expect(await screen.findByText('Adopted')).toBeInTheDocument();
    expect(screen.getByText('@vera')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'claude.ai' })).toHaveAttribute(
      'href',
      'https://claude.ai/code',
    );
    expect(screen.getAllByLabelText('Yes')).toHaveLength(1);
    expect(screen.getByRole('link', { name: 'Open page' })).toHaveAttribute('href', '/folio/p/p1');
    expect(screen.getByText('ai')).toBeInTheDocument();
    expect(screen.getByText('llm')).toBeInTheDocument();
  });
});

describe('columnKey', () => {
  it('makes a free key from the name', () => {
    expect(columnKey('Fecha de alta', [])).toBe('fecha_de_alta');
    expect(columnKey('Status', ['status'])).toBe('status_2');
    expect(columnKey('¿?', [])).toBe('column');
  });
});
