import styled from 'styled-components';

export const Wrap = styled.div`
  min-height: 240px;
  padding: ${({ theme }) => theme.space.md};
  background: ${({ theme }) => theme.color.surface2};
  border-radius: ${({ theme }) => theme.radius.lg};

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
    border-right: 2px solid ${({ theme }) => theme.color.textMuted};
    border-bottom: 2px solid ${({ theme }) => theme.color.textMuted};
    border-bottom-right-radius: 3px;
  }

  .react-grid-item > .react-resizable-handle::after {
    display: none;
  }
`;

export const Block = styled.div<{ $selected: boolean; $invalid: boolean }>`
  box-sizing: border-box;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  padding: ${({ theme }) => theme.space.md};
  background: ${({ theme }) => theme.color.surface};
  border: 2px solid
    ${({ $selected, $invalid, theme }) =>
      $invalid ? theme.color.danger : $selected ? theme.color.accent : theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  cursor: pointer;
`;

export const Head = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
`;

export const Handle = styled.span`
  display: inline-flex;
  cursor: grab;
  color: ${({ theme }) => theme.color.textMuted};

  svg {
    width: 16px;
    height: 16px;
  }
`;

export const Type = styled.span`
  flex: 1;
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.textMuted};
  text-transform: uppercase;
`;

export const Title = styled.strong`
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Summary = styled.span`
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.textMuted};
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;
