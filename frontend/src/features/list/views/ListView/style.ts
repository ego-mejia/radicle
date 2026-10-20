import styled from 'styled-components';

export const Toolbar = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.sm};
  margin: ${({ theme }) => `${theme.space.sm} 0 ${theme.space.md}`};
`;

export const Right = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  margin-left: auto;
`;

export const GroupBy = styled.label`
  display: flex;
  align-items: center;
  gap: 6px;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  white-space: nowrap;

  select {
    width: auto;
    height: 32px;
  }
`;

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
