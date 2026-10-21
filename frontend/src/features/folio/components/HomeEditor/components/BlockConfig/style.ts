import styled from 'styled-components';

export const Panel = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => theme.space.lg};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
`;

export const Heading = styled.h3`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.lg};
`;

export const Problem = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Muted = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.md};
`;
