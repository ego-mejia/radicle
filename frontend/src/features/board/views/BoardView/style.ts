import styled from 'styled-components';

export const Columns = styled.div`
  display: grid;
  grid-template-columns: repeat(3, minmax(240px, 1fr));
  gap: ${({ theme }) => theme.space.md};
  align-items: start;
  overflow-x: auto;
  padding-bottom: ${({ theme }) => theme.space.md};

  @media (max-width: 760px) {
    grid-template-columns: repeat(3, minmax(260px, 85vw));
  }
`;
