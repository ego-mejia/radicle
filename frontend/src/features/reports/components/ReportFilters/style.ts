import styled from 'styled-components';

export const Bar = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.md};
  align-items: flex-end;

  > * {
    min-width: 150px;
  }
`;
