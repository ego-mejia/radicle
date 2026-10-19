import styled from 'styled-components';

export const Panel = styled.aside`
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: ${({ theme }) => theme.space.lg};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  align-self: start;
`;

export const ParentLink = styled.a`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Muted = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Time = styled.div`
  padding: ${({ theme }) => theme.space.sm} 0 ${({ theme }) => theme.space.md};
`;
