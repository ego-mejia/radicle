import styled from 'styled-components';

export const Box = styled.section`
  max-width: 560px;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  color: ${({ theme }) => theme.color.text};
`;
