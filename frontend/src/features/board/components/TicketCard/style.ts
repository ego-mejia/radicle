import styled from 'styled-components';

export const Card = styled.div<{
  $draft: boolean;
  $dragging: boolean;
  $overlay: boolean;
  $dropTarget: boolean;
}>`
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 9px 10px;
  background: ${({ theme }) => theme.color.surface};
  border: 1px ${({ $draft }) => ($draft ? 'dashed' : 'solid')}
    ${({ theme, $draft }) => ($draft ? theme.color.textMuted : theme.color.border)};
  border-radius: ${({ theme }) => theme.radius.md};
  cursor: grab;
  opacity: ${({ $dragging }) => ($dragging ? 0.4 : 1)};
  box-shadow: ${({ theme, $overlay, $dropTarget }) =>
    $overlay
      ? '0 14px 30px rgba(0,0,0,.25)'
      : $dropTarget
        ? `0 -3px 0 0 ${theme.color.accent}`
        : 'none'};
  transform: ${({ $overlay }) => ($overlay ? 'rotate(1.5deg)' : 'none')};
  touch-action: none;
  user-select: none;

  &:hover {
    border-color: ${({ theme }) => theme.color.accent};
  }

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.accent};
    outline-offset: 1px;
  }
`;

export const Top = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
`;

export const Title = styled.div`
  font-size: ${({ theme }) => theme.fontSize.md};
  line-height: 1.35;
  overflow-wrap: anywhere;
`;

export const Bottom = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  min-height: 22px;
`;

export const Spacer = styled.span`
  flex: 1;
`;

export const Tag = styled.span`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.accent};
`;

export const Meta = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.textMuted};

  svg {
    width: 12px;
    height: 12px;
  }
`;

export const Blocked = styled.span`
  display: inline-flex;
  color: ${({ theme }) => theme.color.danger};

  svg {
    width: 14px;
    height: 14px;
  }
`;
