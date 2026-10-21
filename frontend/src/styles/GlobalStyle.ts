import { createGlobalStyle } from 'styled-components';

export const GlobalStyle = createGlobalStyle`
  *, *::before, *::after { box-sizing: border-box; }

  html, body, #root { height: 100%; }

  input[type='radio'],
  input[type='checkbox'] {
    accent-color: ${({ theme }) => theme.color.accent};
  }

  html[data-density='compact'] td,
  html[data-density='compact'] th {
    padding-top: 4px;
    padding-bottom: 4px;
  }

  body {
    margin: 0;
    background: ${({ theme }) => theme.color.bg};
    color: ${({ theme }) => theme.color.text};
    font-family: ${({ theme }) => theme.fonts.ui};
    font-size: ${({ theme }) => theme.fontSize.md};
    line-height: 1.5;
    color-scheme: ${({ theme }) => theme.mode};
    -webkit-font-smoothing: antialiased;
  }

  code, kbd, pre {
    font-family: ${({ theme }) => theme.fonts.mono};
    font-variant-ligatures: none;
  }

  a { color: ${({ theme }) => theme.color.accent}; }

  :focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.accent};
    outline-offset: 2px;
  }

  /* Text that open Folio comments point at (CSS Custom Highlight API). */
  ::highlight(folio-comment) {
    background-color: ${({ theme }) => theme.color.accentSoft};
    text-decoration: underline 2px ${({ theme }) => theme.color.accent};
  }
`;
