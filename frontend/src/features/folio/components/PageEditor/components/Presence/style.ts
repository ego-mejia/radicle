import styled from 'styled-components';

export const Wrap = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Stack = styled.div`
  display: flex;
  align-items: center;
`;

export const Face = styled.span<{ $color: string }>`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  margin-left: -6px;
  border-radius: ${({ theme }) => theme.radius.full};
  border: 2px solid ${({ $color }) => $color};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ $color }) => $color};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 700;

  &:first-child {
    margin-left: 0;
  }
`;

export const More = styled(Face).attrs({ $color: 'currentColor' })`
  color: ${({ theme }) => theme.color.textMuted};
`;

export const AgentChip = styled.span<{ $color: string }>`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  padding: 2px ${({ theme }) => theme.space.sm};
  border-radius: ${({ theme }) => theme.radius.full};
  border: 1px solid ${({ $color }) => $color};
  color: ${({ $color }) => $color};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
`;

export const Hidden = styled.span`
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
`;
