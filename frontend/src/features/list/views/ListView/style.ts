import styled from 'styled-components';

export const Body = styled.div`
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  align-items: start;

  @media (max-width: 900px) {
    grid-template-columns: minmax(0, 1fr);
  }
`;

export const Results = styled.div`
  min-width: 0;
`;
