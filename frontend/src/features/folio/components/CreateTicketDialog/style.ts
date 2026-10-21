import styled from 'styled-components';

export const Form = styled.div`
  display: grid;
  gap: ${({ theme }) => theme.space.md};
`;

export const Quote = styled.p`
  margin: 0;
  padding-left: ${({ theme }) => theme.space.sm};
  border-left: 3px solid ${({ theme }) => theme.color.accent};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.md};
  white-space: pre-wrap;
`;

export const Error = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
  font-size: ${({ theme }) => theme.fontSize.md};
`;
