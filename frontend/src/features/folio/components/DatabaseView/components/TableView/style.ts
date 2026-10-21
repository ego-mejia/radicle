import styled from 'styled-components';

export const Scroll = styled.div`
  overflow-x: auto;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
`;

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: ${({ theme }) => theme.fontSize.md};

  th,
  td {
    padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
    text-align: left;
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
    white-space: nowrap;
  }

  th {
    font-size: ${({ theme }) => theme.fontSize.sm};
    font-weight: 600;
    color: ${({ theme }) => theme.color.textMuted};
    background: ${({ theme }) => theme.color.surface2};
  }

  tbody tr:last-child td {
    border-bottom: 0;
  }

  svg {
    width: 14px;
    height: 14px;
  }
`;

export const Actions = styled.td`
  width: 1%;
  text-align: right;
`;
