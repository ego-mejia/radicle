import styled from 'styled-components';

export const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: ${({ theme }) => theme.space.xs};
`;

export const Done = styled.div`
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.md}`};
  border: 1px dashed ${({ theme }) => theme.color.accentFill};
  border-radius: ${({ theme }) => theme.radius.lg};
  font-size: ${({ theme }) => theme.fontSize.md};

  a {
    color: ${({ theme }) => theme.color.accent};
    font-weight: 600;
  }
`;

export const Tool = styled.span`
  padding: 4px 8px;
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface2};
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Error = styled.p`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.danger};
`;
