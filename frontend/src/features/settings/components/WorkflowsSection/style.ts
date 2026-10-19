import styled from 'styled-components';

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: ${({ theme }) => theme.space.lg};
`;

export const Workflow = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};

  h3 {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.md};
  }
`;

export const Statuses = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
`;

export const Table = styled.table`
  border-collapse: collapse;
  font-size: ${({ theme }) => theme.fontSize.sm};

  td {
    padding: 3px 6px 3px 0;
    color: ${({ theme }) => theme.color.textMuted};
    vertical-align: top;
  }

  td:first-child {
    color: ${({ theme }) => theme.color.text};
    font-weight: 600;
  }
`;
