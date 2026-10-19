import styled from 'styled-components';

export const Columns = styled.div`
  display: grid;
  gap: ${({ theme }) => theme.space.md};
  align-items: start;
  overflow-x: auto;
  padding-bottom: ${({ theme }) => theme.space.md};
`;
