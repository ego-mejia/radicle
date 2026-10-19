import styled from 'styled-components';

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: ${({ theme }) => theme.fontSize.md};

  th,
  td {
    text-align: left;
    padding: 8px 6px;
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
  }

  th {
    color: ${({ theme }) => theme.color.textMuted};
    font-weight: 500;
  }
`;

export const Error = styled.div`
  margin-top: 4px;
  color: ${({ theme }) => theme.color.danger};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Muted = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;
