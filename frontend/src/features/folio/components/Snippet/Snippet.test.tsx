import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { Snippet } from '.';
import { hitTarget } from './hitTarget';

describe('Snippet', () => {
  it('highlights the matched words', async () => {
    renderWithProviders(
      <p data-testid="hit">
        <Snippet text="Crea el **agente** y su **token**." />
      </p>,
    );
    const hit = await screen.findByTestId('hit');
    const marks = [...hit.querySelectorAll('mark')].map((m) => m.textContent);
    expect(marks).toEqual(['agente', 'token']);
    expect(hit).toHaveTextContent('Crea el agente y su token.');
  });

  it('reads the page and the section from a hit url', () => {
    expect(hitTarget('/folio/p/abc-guia#conecta')).toEqual({ page: 'abc-guia', hash: 'conecta' });
    expect(hitTarget('/folio/p/abc-guia')).toEqual({ page: 'abc-guia', hash: undefined });
  });
});
