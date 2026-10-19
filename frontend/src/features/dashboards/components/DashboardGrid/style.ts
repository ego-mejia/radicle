import styled from 'styled-components';

export const Wrap = styled.div<{ $editing: boolean }>`
  .react-grid-item.react-grid-placeholder {
    background: ${({ theme }) => theme.color.accentSoft};
    border-radius: ${({ theme }) => theme.radius.md};
    opacity: 1;
  }

  .react-resizable-handle {
    position: absolute;
    right: 2px;
    bottom: 2px;
    width: 14px;
    height: 14px;
    cursor: se-resize;
    display: ${({ $editing }) => ($editing ? 'block' : 'none')};
    border-right: 2px solid ${({ theme }) => theme.color.textMuted};
    border-bottom: 2px solid ${({ theme }) => theme.color.textMuted};
    border-bottom-right-radius: 3px;
  }

  .react-grid-item > .react-resizable-handle::after {
    display: none;
  }
`;
