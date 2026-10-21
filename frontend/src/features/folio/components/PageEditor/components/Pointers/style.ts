import styled from 'styled-components';

export const Layer = styled.div`
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
`;

export const Pointer = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  display: flex;
  align-items: flex-start;
  transition: transform 80ms linear;
`;

export const Name = styled.span<{ $color: string }>`
  margin: 14px 0 0 -4px;
  padding: 1px ${({ theme }) => theme.space.xs};
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ $color }) => $color};
  color: ${({ theme }) => theme.color.surface};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 600;
  white-space: nowrap;
`;
