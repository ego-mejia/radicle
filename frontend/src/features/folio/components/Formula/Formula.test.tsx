import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { b, doc, p, t } from '../DocContent/testDoc';
import { DocContent } from '../DocContent';

describe('Formula', () => {
  it('renders block and inline formulas with KaTeX', async () => {
    const page = doc(
      b('formula', { latex: 'E = mc^2' }),
      p(t('Vale '), { type: 'inlineFormula', attrs: { latex: 'a^2' } }),
    );
    const { container } = renderWithProviders(<DocContent doc={page} />);
    await waitFor(() => expect(container.querySelectorAll('.katex')).toHaveLength(2));
    expect(container.querySelector('.katex-display')).not.toBeNull();
    expect(container.querySelector('p .katex')).not.toBeNull();
  });

  it('shows the LaTeX when it does not compile', async () => {
    renderWithProviders(<DocContent doc={doc(b('formula', { latex: '\\frac{1' }))} />);
    await waitFor(() =>
      expect(screen.getByText('\\frac{1')).toHaveAttribute('title', "This formula doesn't compile"),
    );
  });
});
