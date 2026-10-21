import styled from 'styled-components';

export const Meta = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  white-space: nowrap;
`;
