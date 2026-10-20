import { render, screen } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { describe, expect, it } from 'vitest';
import { lightTheme } from '../../../styles/theme';
import { Logo } from '.';

describe('Logo', () => {
  it('is Radi: a green tile with two eyes', () => {
    render(
      <ThemeProvider theme={lightTheme}>
        <Logo size={26} />
      </ThemeProvider>,
    );
    const logo = screen.getByRole('img', { name: 'Radicle' });
    expect(logo).toHaveAttribute('width', '26');
    expect(logo.querySelectorAll('.badge')).toHaveLength(1);
    expect(logo.querySelectorAll('.eye')).toHaveLength(2);
  });
});
