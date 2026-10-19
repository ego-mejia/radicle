import styled from 'styled-components';

export const Frame = styled.div`
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  overflow: hidden;

  &:focus-within {
    border-color: ${({ theme }) => theme.color.accent};
    box-shadow: 0 0 0 2px ${({ theme }) => theme.color.accentSoft};
  }

  .cm-editor {
    min-height: ${({ theme }) => theme.space.xxl};
    max-height: 420px;
    font-size: 13px;
    background: transparent;
    color: ${({ theme }) => theme.color.text};
  }

  .cm-editor.cm-focused {
    outline: none;
  }

  .cm-scroller {
    font-family: ${({ theme }) => theme.fonts.mono};
    line-height: 1.55;
  }

  .cm-content {
    padding: 8px 4px;
    caret-color: ${({ theme }) => theme.color.accent};
  }

  .cm-placeholder {
    color: ${({ theme }) => theme.color.textMuted};
  }

  .cm-tooltip {
    border: 1px solid ${({ theme }) => theme.color.border};
    background: ${({ theme }) => theme.color.surface};
    color: ${({ theme }) => theme.color.text};
  }

  .cm-tooltip-autocomplete ul li[aria-selected] {
    background: ${({ theme }) => theme.color.accentSoft};
    color: ${({ theme }) => theme.color.text};
  }

  .cm-selectionBackground,
  .cm-editor.cm-focused .cm-selectionBackground {
    background: ${({ theme }) => theme.color.accentSoft} !important;
  }
`;
