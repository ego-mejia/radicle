import styled from 'styled-components';

export const Log = styled.ul`
  list-style: none;
  margin: 0 0 ${({ theme }) => theme.space.md};
  padding: 0 0 0 ${({ theme }) => theme.space.xl};
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};

  li {
    display: flex;
    gap: ${({ theme }) => theme.space.sm};
    align-items: center;
    font-size: ${({ theme }) => theme.fontSize.sm};
  }
`;
