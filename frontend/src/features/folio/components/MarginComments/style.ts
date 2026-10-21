import styled from 'styled-components';

export const Margin = styled.aside`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  font-size: ${({ theme }) => theme.fontSize.md};
`;
