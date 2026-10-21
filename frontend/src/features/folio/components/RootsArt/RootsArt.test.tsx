import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { RootsArt } from '.';

describe('RootsArt', () => {
  it('draws decorative roots hidden from screen readers', () => {
    const { container } = render(<RootsArt />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('aria-hidden');
    expect(svg?.querySelectorAll('path')).toHaveLength(4);
  });
});
