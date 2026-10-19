import styled from 'styled-components';

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: ${({ theme }) => theme.space.md};
`;

export const Check = styled.input`
  width: 18px;
  height: 18px;
  margin: 8px 0;
`;
