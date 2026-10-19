import styled from 'styled-components';

export const Help = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Detail = styled.p`
  margin: 0;
  padding: ${({ theme }) => theme.space.sm} ${({ theme }) => theme.space.md};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface2};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
